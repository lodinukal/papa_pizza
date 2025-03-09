from abc import ABC, abstractmethod
from enum import Enum
import typing
import time
import os
import json
import random


class Status(Enum):
    PENDING = 1
    IN_PROGRESS = 2
    CANCELLED = 3
    DONE = 4


class Item:
    def __init__(self, name, price):
        self.name = name
        self.price = price

    def __str__(self):
        return f"{self.name} - {self.price}"


all_items = {
    "Pepperoni": Item("Pepperoni", 21.00),
    "Chicken Supreme": Item("Chicken Supreme", 23.50),
    "BBQ Meatlovers": Item("BBQ Meatlovers", 25.50),
    "Veg Supreme": Item("Veg Supreme", 22.50),
    "Hawaiian": Item("Hawaiian", 19.00),
    "Margherita": Item("Margherita", 18.50),
}


class Customer:
    def __init__(self, name: str, phone: str):
        self.name = name
        self.phone = phone
        self.loyalty_member = False

    def __str__(self):
        return f"{self.name} ({self.phone})"

    def is_eligible_for_discount(self):
        return self.loyalty_member

    def set_loyalty_member(self, is_member: bool):
        self.loyalty_member = is_member


class OrderCost:
    raw_cost: float
    discount: float
    delivery_cost: float
    cost_before_gst: float
    gst: float
    cost_after_gst: float

    def __init__(self):
        self.raw_cost = 0.0
        self.discount = 0.0
        self.delivery_cost = 0.0
        self.cost_before_gst = 0.0
        self.gst = 0.0
        self.cost_after_gst = 0.0


class Order:
    def __init__(self, customer: Customer, items: dict[str, int]):
        self.customer = customer
        self.time = time.time()
        self.completed_time = None
        self.status = Status.PENDING
        self.items = items
        self.is_home_delivery = False
        self.id = random.randint(1000, 9999)

    def __str__(self):
        return self.small_repr()

    def small_repr(self):
        time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.time))
        return (
            f"{self.id}|{time_str}| {self.customer} - {self.items} - {self.status.name}"
        )

    def full_repr(self):
        time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.time))
        lines = [
            f"Order {self.id} for {self.customer} at {time_str}",
            "Items:",
        ]
        for item, count in self.items.items():
            lines.append(
                f"\t- {item} x {count} (${all_items[item].price:.2f} each, ${all_items[item].price * count:.2f} total)"
            )
        lines.append(f"Status: {self.status.name}")
        if self.is_home_delivery:
            lines.append("Home delivery")
        if self.status == Status.DONE:
            completed_time_str = time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(self.completed_time)
            )
            lines.append(f"Completed at {completed_time_str}")
        costs = self.cost()
        lines.append(f"Gross: ${costs.raw_cost:.2f}")
        if costs.discount > 0:
            lines.append(f"Discount: ${costs.discount:.2f}")
        if costs.delivery_cost > 0:
            lines.append(f"Delivery: ${costs.delivery_cost:.2f}")
        lines.append(f"GST: ${costs.gst:.2f}")
        lines.append(f"Total: ${costs.cost_after_gst:.2f}")
        return "\n".join(lines)

    def mark_in_progress(self):
        self.status = Status.IN_PROGRESS

    def mark_cancelled(self):
        self.status = Status.CANCELLED

    def mark_done(self):
        self.status = Status.DONE
        self.completed_time = time.time()

    def cost(self) -> OrderCost:
        costing = OrderCost()
        costing.raw_cost = sum(
            all_items[item].price * count for item, count in self.items.items()
        )

        # check if the customer can receive a discount
        over_100 = costing.raw_cost > 100
        if self.customer.is_eligible_for_discount() and over_100:
            # 5% discount
            costing.discount = costing.raw_cost * 0.05

        if self.is_home_delivery:
            costing.delivery_cost = 5.0

        costing.cost_before_gst = (
            costing.raw_cost - costing.discount + costing.delivery_cost
        )
        # 10% tax
        costing.gst = costing.cost_before_gst * 0.1
        costing.cost_after_gst = costing.cost_before_gst + costing.gst

        return costing

    def toJSON(self):
        return {
            "customer": self.customer.phone,
            "time": self.time,
            "status": self.status.name,
            "items": {item: count for item, count in self.items.items()},
            "is_home_delivery": self.is_home_delivery,
            "id": self.id,
            "completed_time": self.completed_time,
        }

    def fromJSON(self, data):
        self.time = data["time"]
        self.status = Status[data["status"]]
        self.is_home_delivery = data["is_home_delivery"]
        self.id = data["id"]
        if "completed_time" in data:
            self.completed_time = data["completed_time"]


class IStore(ABC):
    @abstractmethod
    def get_all_time_orders(self) -> list[Order]:
        pass

    @abstractmethod
    def get_date_orders(self, time: float = time.time()) -> list[Order]:
        pass

    @abstractmethod
    def add_order(
        self, customer: Customer, items: dict[str, int], is_home_delivery: bool
    ) -> Order:
        pass

    @abstractmethod
    def get_customer(self, phone: str) -> typing.Optional[Customer]:
        pass

    @abstractmethod
    def customer_phones(self) -> list[Customer]:
        pass

    @abstractmethod
    def add_customer(self, customer: Customer):
        pass

    @abstractmethod
    def get_or_add_customer(self, phone: str, name: str) -> Customer:
        pass

    @abstractmethod
    def complete_order(self, order: Order):
        pass

    @abstractmethod
    def cancel_order(self, order: Order):
        pass

    @abstractmethod
    def clear_orders(self):
        pass


class FileSystemStoreData:
    # phone number to customer
    all_customers: dict[str, Customer]
    active_orders: list[Order]

    def __init__(self):
        self.all_customers = {}
        self.active_orders = []

    def toJSON(self):
        all_customers = {
            k: {"name": v.name, "phone": v.phone, "loyalty_member": v.loyalty_member}
            for k, v in self.all_customers.items()
        }
        active_orders = [
            {
                "customer": order.customer.phone,
                "time": order.time,
                "status": order.status.name,
                "items": {item: count for item, count in order.items.items()},
                "is_home_delivery": order.is_home_delivery,
                "id": order.id,
            }
            for order in self.active_orders
        ]

        return {
            "all_customers": all_customers,
            "active_orders": active_orders,
        }

    def fromJSON(self, data):
        self.all_customers = {
            k: Customer(v["name"], v["phone"]) for k, v in data["all_customers"].items()
        }
        for order in data["active_orders"]:
            customer = self.all_customers[order["customer"]]
            new_order = Order(
                customer, {item: count for item, count in order["items"].items()}
            )
            new_order.fromJSON(order)
            self.active_orders.append(new_order)


class DataError(Exception):
    message: str

    def __init__(self, message: str):
        self.message = message


class FileSystemStore(IStore):
    data: FileSystemStoreData

    file_path: str

    def __init__(self, file_path: str = "store.json"):
        self.file_path = file_path
        self.data = FileSystemStoreData()

        # check if file exists
        if os.path.exists(file_path):
            self.load()

    def load(self):
        with open(self.file_path, "r") as file:
            data = file.read()
            self.data.fromJSON(json.loads(data))

    def save(self):
        with open(self.file_path, "w") as file:
            file.write(json.dumps(self.data.toJSON()))

    def get_all_time_orders(self) -> list[Order]:
        all_orders = list(self.data.active_orders)
        return all_orders

    def get_date_orders(self, t: float = time.time()) -> list[Order]:
        day = time.localtime(t).tm_yday
        today_orders = [
            order
            for order in self.data.active_orders
            if time.localtime(order.time).tm_yday == day
        ]
        return today_orders

    def add_order(
        self, customer: Customer, items: list[Item], is_home_delivery: bool
    ) -> Order:
        order = Order(customer, items)
        order.is_home_delivery = is_home_delivery

        self.data.active_orders.append(order)
        self.save()

        return order

    def get_customer(self, phone: str) -> typing.Optional[Customer]:
        return self.data.all_customers.get(phone)

    def customer_phones(self) -> list[str]:
        return list(self.data.all_customers.keys())

    def complete_order(self, order: Order):
        self.data.active_orders.remove(order)
        self.data.completed_orders.append(order)
        self.save()

    def cancel_order(self, order: Order):
        self.data.active_orders.remove(order)
        self.save()

    def add_customer(self, customer: Customer):
        if customer.phone in self.data.all_customers:
            raise DataError("Customer already exists")
        self.data.all_customers[customer.phone] = customer
        self.save()

    def get_or_add_customer(self, phone: str, name: str) -> Customer:
        customer = self.data.all_customers.get(phone)
        if not customer:
            customer = Customer(name, phone)
            self.data.all_customers[phone] = customer
            self.save()
        return customer

    def set_customer_loyalty(self, phone: str, is_member: bool):
        customer = self.data.all_customers.get(phone)
        if customer:
            customer.set_loyalty_member(is_member)
            self.save()
        else:
            print("Customer not found")

    def clear_orders(self):
        self.data.active_orders.clear()
        self.data.completed_orders.clear()
        self.save()

from abc import ABC, abstractmethod
from enum import Enum
import typing
import time
import os
import json
import random


# Represents the status of an order
# PENDING: The order has been placed but not yet started
# IN_PROGRESS: The order is being prepared
# CANCELLED: The order has been cancelled
# DONE: The order has been completed
class Status(Enum):
    PENDING = 1
    IN_PROGRESS = 2
    CANCELLED = 3
    DONE = 4


# Represents an item in the menu
# name: The name of the item
# price: The price of the item
class Item:
    def __init__(self, name, price):
        self.name = name
        self.price = price

    def __str__(self):
        return f"{self.name} - {self.price}"


# a dictionary of all items in the menu
all_items = {
    "Pepperoni": Item("Pepperoni", 21.00),
    "Chicken Supreme": Item("Chicken Supreme", 23.50),
    "BBQ Meatlovers": Item("BBQ Meatlovers", 25.50),
    "Veg Supreme": Item("Veg Supreme", 22.50),
    "Hawaiian": Item("Hawaiian", 19.00),
    "Margherita": Item("Margherita", 18.50),
}


# A customer who can place orders, identified by their phone number
# name: The name of the customer
# phone: The phone number of the customer
# loyalty_member: Whether the customer is a loyalty member or not, and thus eligible for discounts
class Customer:
    def __init__(self, name: str, phone: str):
        self.name = name
        self.phone = phone
        self.loyalty_member = False

    def __str__(self):
        return f"{self.name} ({self.phone})"

    # getter for loyalty_member
    def is_eligible_for_discount(self):
        return self.loyalty_member

    # setter for loyalty_member
    def set_loyalty_member(self, is_member: bool):
        self.loyalty_member = is_member


# class to calculate the cost of an order and give each component of the cost
# raw_cost: the total cost of all items in the order
# discount: the discount applied to the order
# delivery_cost: the cost of delivery if applicable
# cost_before_gst: the total cost before GST
# gst: the GST applied to the total cost
# cost_after_gst: the total cost after GST
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

    # adds one or more items by name and quantity to the order
    def add_items(self, item_name: str, quantity: int):
        self.raw_cost += all_items[item_name].price * quantity

    # makes the delivery cost $8.0 if the order is a home delivery
    def add_deliver_cost(self):
        self.delivery_cost = 8.0

    # adds a 5% discount to the order
    def add_discount(self):
        self.discount = self.raw_cost * 0.05

    # checks if the discount can be applied to the order
    def can_discount_apply(self):
        return self.raw_cost > 100

    # calculates the cost before GST
    def calculate_pre_gst_cost(self):
        self.cost_before_gst = self.raw_cost - self.discount + self.delivery_cost

    # calculates the GST
    # note: will call calculate_pre_gst_cost() to ensure cost_before_gst is up to date
    def calculate_gst(self):
        self.calculate_pre_gst_cost()
        self.gst = self.cost_before_gst * 0.1

    # calculates the total cost of the order
    # note: will call calculate_gst() to ensure gst is up to date
    def calculate_total_cost(self):
        self.calculate_gst()
        self.cost_after_gst = self.cost_before_gst + self.gst

    # returns the total cost of the order after GST (customer payment amount)
    # note: will call calculate_total_cost() to ensure cost_after_gst is up to date
    def get_total_cost(self):
        self.calculate_total_cost()
        return self.cost_after_gst


# Represents an order placed by a customer
# customer: The customer who placed the order
# time: The time the order was placed
# completed_time: The time the order was completed, optional, defaults to None
# status: The status of the order
# items: A dictionary of items in the order and their quantities
# is_home_delivery: Whether the order is a home delivery or not
# id: A unique identifier for the order
class Order:
    def __init__(self, customer: Customer, items: dict[str, int]):
        self.customer = customer
        self.time = time.time()
        self.completed_time = None
        self.status = Status.PENDING
        self.items = items
        self.is_home_delivery = False
        self.id = random.randint(1000, 9999)

    # allows for us to print the Order object in a readable format
    def __str__(self):
        return self.small_repr()

    # returns a condensed version of the order
    # e.g. "1234|2021-09-01 12:00:00| John Doe - {'Pepperoni': 2, 'Hawaiian': 1} - PENDING"
    def small_repr(self):
        time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.time))
        return (
            f"{self.id}|{time_str}| {self.customer} - {self.items} - {self.status.name}"
        )

    # returns a full version of the order, with all details
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

    # marks the order as in progress
    def mark_in_progress(self):
        self.status = Status.IN_PROGRESS

    # marks the order as cancelled
    def mark_cancelled(self):
        self.status = Status.CANCELLED

    # marks the order as done
    # will set the completed_time to the current time
    def mark_done(self):
        self.status = Status.DONE
        self.completed_time = time.time()

    # calculates the cost of the order
    # returns an OrderCost object
    def cost(self) -> OrderCost:
        costing = OrderCost()
        for item, count in self.items.items():
            costing.add_items(item, count)
        if self.customer.is_eligible_for_discount() and costing.can_discount_apply():
            costing.add_discount()
        if self.is_home_delivery:
            costing.add_deliver_cost()
        costing.get_total_cost()
        return costing

    # serializes the order to a JSON object for saving/loading
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

    # deserializes the order from a JSON object
    # note: will not set the customer, as it is not stored in the JSON object
    def fromJSON(self, data):
        self.time = data["time"]
        self.status = Status[data["status"]]
        self.is_home_delivery = data["is_home_delivery"]
        self.id = data["id"]
        if "completed_time" in data:
            self.completed_time = data["completed_time"]


# Abstract class for a store that can store and retrieve orders and customers
class IStore(ABC):
    # get_all_time_orders: returns all orders ever placed
    @abstractmethod
    def get_all_time_orders(self) -> list[Order]:
        pass

    # get_date_orders: returns all orders placed on a given day
    @abstractmethod
    def get_date_orders(self, time: float = time.time()) -> list[Order]:
        pass

    # add_order: adds an order to the store
    @abstractmethod
    def add_order(
        self, customer: Customer, items: dict[str, int], is_home_delivery: bool
    ) -> Order:
        pass

    # get_customer: returns a customer by phone number
    @abstractmethod
    def get_customer(self, phone: str) -> typing.Optional[Customer]:
        pass

    # customer_phones: returns a list of all customer phone numbers
    @abstractmethod
    def customer_phones(self) -> list[Customer]:
        pass

    # set_customer_loyalty: sets a customer's loyalty status
    # can return an error if the customer already exists
    @abstractmethod
    def add_customer(self, customer: Customer):
        pass

    # get_or_add_customer: returns a customer by phone number, or creates a new one if not found
    @abstractmethod
    def get_or_add_customer(self, phone: str, name: str) -> Customer:
        pass

    # clear_orders: clears all orders from the store (not used regularly)
    @abstractmethod
    def clear_orders(self):
        pass


# a class used to store PURELY data about the customers and orders
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
        active_orders = [order.toJSON() for order in self.active_orders]

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


# exception class for data errors in the store
class DataError(Exception):
    message: str

    def __init__(self, message: str):
        self.message = message


# subclass of IStore that stores data in a JSON file on disk
class FileSystemStore(IStore):
    data: FileSystemStoreData

    file_path: str

    def __init__(self, file_path: str = "store.json"):
        self.file_path = file_path
        self.data = FileSystemStoreData()

        # check if file exists
        if os.path.exists(file_path):
            self.load()

    # loads data from the file, don't usually need to call this directly as the contructor does it
    def load(self):
        with open(self.file_path, "r") as file:
            data = file.read()
            self.data.fromJSON(json.loads(data))

    # saves data to the file
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
        self.save()

import typing
from abc import abstractmethod

from database import Customer, DataError, IStore, all_items, Status
from fake import fake_customer, fake_order

import time


# a context object which stores the store object
# more objects can be added here if needed
# this avoids using too many global variables
# and makes it easier to test the code (as we can just replace the context object)
class Context:
    store: IStore

    def __init__(self, store: IStore):
        self.store = store


# default context used by cli commands
cli_context: Context = None


# a parent class for all commands
# it will register all commands in a dictionary
class Command:
    name: str
    description: str

    all_commands: dict[str, "Command"] = {}

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.all_commands[name] = self

    @abstractmethod
    def execute(self, args: typing.List[str]) -> typing.Optional[str]:
        pass


# a help command to direct users to other commands and show their usage
class HelpCommand(Command):
    def __init__(self):
        super().__init__("help", "Prints a help message, usage: help <command>?")

    def execute(self, args: typing.List[str]) -> typing.Optional[str]:
        if len(args) > 0:
            command = Command.all_commands.get(args[0])
            if command:
                return f"{command.name}: {command.description}"
            return f"Command {args[0]} not found"
        print(
            "Available commands: " + ", ".join([c for c in Command.all_commands.keys()])
        )
        return None


# a command to view all orders, for the day or all time
class ViewActiveOrdersCommand(Command):
    def __init__(self):
        super().__init__(
            "view_orders",
            "View all active orders, using a true flag if all orders of all time should be shown otherwise just today, usage: view_orders <all_time>?",
        )

    def execute(self, args: typing.List[str]) -> typing.Optional[str]:
        all_time = False
        if len(args) > 0 and args[0].lower() == "true":
            all_time = True

        orders = (
            cli_context.store.get_all_time_orders()
            if all_time
            else cli_context.store.get_date_orders()
        )
        if not orders or len(orders) == 0:
            return "No orders found"
        orders.sort(key=lambda x: (-x.status.value, x.time))

        active_orders = []
        completed_orders = []

        for order in orders:
            if order.status == Status.DONE:
                completed_orders.append(order)
            else:
                active_orders.append(order)

        print("Today's orders:" if not all_time else "All time orders:")
        print("Active orders:")
        print("\n".join([str(order) for order in active_orders]))
        print("Completed orders:")
        print("\n".join([str(order) for order in completed_orders]))
        return None


# provides a summary of the day's sales, if no argument is provided, it will show today's saless
class DailySummaryCommand(Command):
    def __init__(self):
        super().__init__(
            "daily_summary",
            "View daily summary, for today or another day, usage: daily_summary <date>?",
        )

    def execute(self, args: typing.List[str]) -> typing.Optional[str]:
        date = time.time()
        if len(args) > 0:
            try:
                t = time.strptime(args[0], "%Y-%m-%d")
                date = time.mktime(t)
            except ValueError:
                return "Invalid date format, use YYYY-MM-DD"

        time_str = time.strftime("%Y-%m-%d", time.localtime(date))

        orders = cli_context.store.get_date_orders(date)
        if not orders or len(orders) == 0:
            return f"No orders on {time_str}"

        total_orders = 0
        total_sales = 0
        total_delivery_sales = 0

        all_items_sold = dict()

        for order in orders:
            if order.status != Status.DONE:
                continue
            total_orders += 1
            cost = order.cost()
            total_sales += cost.cost_before_gst
            if order.is_home_delivery:
                total_delivery_sales += cost.cost_before_gst
            for item, count in order.items.items():
                if item not in all_items_sold:
                    all_items_sold[item] = 0
                all_items_sold[item] += count

        print(f"Summary for {time_str}:")
        print(f"Total orders: {total_orders}")
        print(f"Total sales: ${total_sales}")
        print(f"Total delivery sales: ${total_delivery_sales}")

        print("Items sold:")
        for item, count in all_items_sold.items():
            print(f"\t- {item}: {count}")

        return None


# testing, just generates a lot of customers
class FakeCustomersCommand(Command):
    def __init__(self):
        super().__init__(
            "fake_customers",
            "Generate fake customers and add them to the store, usage: fake_customers <count>",
        )

    def execute(self, args: typing.List[str]) -> typing.Optional[str]:
        if len(args) < 1:
            return "Usage: fake_customers <count>"

        try:
            count = int(args[0])
            for _ in range(count):
                customer = fake_customer()
                cli_context.store.get_or_add_customer(customer.phone, customer.name)
            return f"Added {count} customers"
        except ValueError:
            return "Invalid count"


import random


# testing, just generates a lot of orders
class FakeOrdersCommand(Command):
    def __init__(self):
        super().__init__(
            "fake_orders",
            "Generate fake orders and add them to the store, usage: fake_orders <count>",
        )

    def execute(self, args: typing.List[str]) -> typing.Optional[str]:
        if len(args) < 1:
            return "Usage: fake_orders <count>"

        try:
            count = int(args[0])
            for _ in range(count):
                items, home_delivery, order_time = fake_order()
                phone_random = random.choice(cli_context.store.customer_phones())
                customer = cli_context.store.get_customer(phone_random)
                order = cli_context.store.add_order(customer, items, home_delivery)
                order.time = order_time
            return f"Added {count} orders"
        except ValueError:
            return "Invalid count"


# sets an order as in progress
class MarkInProgressCommand(Command):
    def __init__(self):
        super().__init__(
            "mark_in_progress",
            "Mark an order as in progress, usage: mark_in_progress <order_id>",
        )

    def execute(self, args: typing.List[str]) -> typing.Optional[str]:
        if len(args) < 1:
            return "Usage: mark_in_progress <order_id>"

        order_id_str = args[0]
        try:
            order_id = int(order_id_str)
            order = next(
                (
                    order
                    for order in cli_context.store.get_all_time_orders()
                    if order.id == order_id
                ),
                None,
            )
        except ValueError:
            return "Invalid order id"
        if not order:
            return "Order not found"

        order.mark_in_progress()
        return f"Marked order {order_id} as in progress"


# sets an order as cancelled
class MarkCancelledCommand(Command):
    def __init__(self):
        super().__init__(
            "mark_cancelled",
            "Mark an order as cancelled, usage: mark_cancelled <order_id>",
        )

    def execute(self, args: typing.List[str]) -> typing.Optional[str]:
        if len(args) < 1:
            return "Usage: mark_cancelled <order_id>"

        order_id_str = args[0]
        try:
            order_id = int(order_id_str)
            order = next(
                (
                    order
                    for order in cli_context.store.get_all_time_orders()
                    if order.id == order_id
                ),
                None,
            )
        except ValueError:
            return "Invalid order id"
        if not order:
            return "Order not found"

        order.mark_cancelled()
        return f"Marked order {order_id} as cancelled"


# sets an order as done
class MarkDoneCommand(Command):
    def __init__(self):
        super().__init__(
            "mark_done",
            "Mark an order as done, usage: mark_done <order_id>",
        )

    def execute(self, args: typing.List[str]) -> typing.Optional[str]:
        if len(args) < 1:
            return "Usage: mark_done <order_id>"

        order_id_str = args[0]
        try:
            order_id = int(order_id_str)
            order = next(
                (
                    order
                    for order in cli_context.store.get_all_time_orders()
                    if order.id == order_id
                ),
                None,
            )
        except ValueError:
            return "Invalid order id"
        if not order:
            return "Order not found"

        order.mark_done()
        return f"Marked order {order_id} as completed"


# adds a new customer
class AddCustomerCommand(Command):
    def __init__(self):
        super().__init__(
            "add_customer", "Add a new customer, usage: add_customer <phone> <name>"
        )

    def execute(self, args: typing.List[str]) -> typing.Optional[str]:
        if len(args) < 2:
            return "Usage: add_customer <phone> <name>"

        phone = args[0]
        name = " ".join(args[1:])

        try:
            cli_context.store.add_customer(customer=Customer(phone=phone, name=name))
        except DataError as e:
            return f"Error adding customer: {e}"
        return f"Added customer {name} with phone number {phone}"


# sets a customer as a loyalty member or not
class SetCustomerLoyaltyCommand(Command):
    def __init__(self):
        super().__init__(
            "set_loyalty",
            "Set loyalty status for a customer by phone number, usage: set_loyalty <phone> <loyalty_status>",
        )

    def execute(self, args: typing.List[str]) -> typing.Optional[str]:
        if len(args) < 2:
            return "Usage: set_loyalty <phone> <loyalty_status>"

        phone = args[0]
        loyalty_status = args[1].lower() == "true"
        customer = cli_context.store.get_customer(phone)
        if not customer:
            return "Customer not found"

        customer.loyalty_member = loyalty_status
        return f"Set loyalty status for {phone} to {loyalty_status}"


# adds a new order, prompts the user for items and quantities and additional information
class StartOrderCommand(Command):
    available_item_str = ",\n".join([f"\t- {item}" for item in all_items])

    def __init__(self):
        super().__init__("start_order", "Start a new order for a customer")

    def execute(self, args: typing.List[str]) -> typing.Optional[str]:
        if len(args) < 1:
            return "Usage: start_order <phone>"

        phone = args[0]
        customer = cli_context.store.get_customer(phone)
        if not customer:
            return "Customer not found"

        items = dict()
        while True:
            item = input("Enter item name or press enter to finish: ")
            if item == "":
                break
            if item not in all_items:
                print(f"Unknown item `{item}`")
                print(f"Available items are:\n{self.available_item_str}")
                continue
            try:
                count = int(input("Enter item count: "))
                if count < 1:
                    print("Invalid count, cannot add negative or zero items")
                    continue
                if item not in items:
                    items[item] = count
                else:
                    items[item] += count
            except ValueError:
                print("Invalid count")
                continue

        print("Items in order:")
        for item, count in items.items():
            print(f"\t- {item} x {count}")

        wants_delivery = input("Is this a home delivery? (y/n): ").lower() == "y"
        order = cli_context.store.add_order(customer, items, wants_delivery)

        print(f"Order details:\n{order}")
        return


# gives the full order information for a given order id
class OrderInfoCommand(Command):
    def __init__(self):
        super().__init__(
            "order_info", "Get information about an order, usage: order_info <order_id>"
        )

    def execute(self, args: typing.List[str]) -> typing.Optional[str]:
        if len(args) < 1:
            return "Usage: order_info <order_id>"

        order_id_str = args[0]
        try:
            order_id = int(order_id_str)
            order = next(
                (
                    order
                    for order in cli_context.store.get_all_time_orders()
                    if order.id == order_id
                ),
                None,
            )
        except ValueError:
            return "Invalid order id"
        if not order:
            return "Order not found"
        return order.full_repr()


# register all commands
for c in Command.__subclasses__():
    c()


initial_prompt = """Welcome to the pizza store command line interface
To begin, use the `help` command to see available commands
and `exit` to exit the program

Press ctrl-c to interrupt a command and ctrl-c twice on the command prompt to exit

Some basic information:
add_customer <phone> <name> - add a new customer
set_loyalty <phone> <loyalty_status> - set loyalty status for a customer, where phone is the phone number and loyalty_status is true or false
start_order <phone> - start a new order for a customer
order_info <order_id> - get information about an order
view_orders - view orders for today
view_orders true - view all orders for all time
daily_summary - view daily summary for today
daily_summary <date> - view daily summary for a specific date in the format YYYY-MM-DD
mark_in_progress <order_id> - mark an order as in progress
mark_done <order_id> - mark an order as done
mark_cancelled <order_id> - mark an order as cancelled

utility commands:
fake_customers <count> - generate fake customers
fake_orders <count> - generate fake orders using existing customers
help <command>? - get help on a specific command, i.e. `help add_customer`
"""


# the main loop for the command line interface
def loop(context: Context):
    global cli_context
    old_context = cli_context
    cli_context = context
    exited_once = False
    print(initial_prompt)
    while True:
        # exception handling to prevent ctrl+c from exiting the program directly
        try:
            command_string = input("Enter command: ")
        except KeyboardInterrupt:
            if exited_once:
                break
            exited_once = True
            print("\nPress Ctrl+C again to exit")
            continue
        exited_once = False
        split_command = command_string.split(" ")
        command_word = split_command[0]
        command_args = split_command[1:]
        # exit is a default command to exit the program
        if command_word == "exit":
            break

        found = False
        if command_word in Command.all_commands:
            found = True
            try:
                message = Command.all_commands[command_word].execute(command_args)
            except KeyboardInterrupt:
                print("\nCommand interrupted\n")
                message = None
            except:
                print("Unexpected error from command")
                message = None
            if message:
                print(message)

        if not found:
            print(
                "Unknown command, use `help` to see available commands\nand `exit` to exit"
            )

    cli_context = old_context

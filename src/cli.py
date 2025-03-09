import typing
from abc import ABC, abstractmethod

from database import Customer, DataError, IStore, all_items


class Context:
    store: IStore

    def __init__(self, store: IStore):
        self.store = store


cli_context: Context = None


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


class ViewActiveOrdersCommand(Command):
    def __init__(self):
        super().__init__("view_orders", "View all active orders")

    def execute(self, args: typing.List[str]) -> typing.Optional[str]:
        orders = cli_context.store.get_active_orders()
        if not orders or len(orders) == 0:
            return "No orders found"

        print("\n".join([str(order) for order in orders]))
        return None


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
                if count < 0:
                    print("Invalid count, cannot add negative items")
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
                    for order in cli_context.store.get_active_orders()
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


def loop(context: Context):
    global cli_context
    old_context = cli_context
    cli_context = context
    exited_once = False
    while True:
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
        if command_word == "exit":
            break

        found = False
        if command_word in Command.all_commands:
            found = True
            message = Command.all_commands[command_word].execute(command_args)
            if message:
                print(message)

        if not found:
            print(
                "Unknown command, use `help` to see available commands\nand `exit` to exit"
            )

    cli_context = old_context

from faker import Faker
from database import IStore, Customer, all_items

fake = Faker()


def fake_customer() -> Customer:
    customer = Customer(fake.name(), fake.phone_number())
    customer.set_loyalty_member(fake.boolean())
    return customer


def fake_order() -> tuple[dict[str, int], bool, float]:
    items = dict()
    for _ in range(fake.random_int(1, 5)):
        item = fake.random_element(all_items.keys())
        items[item] = fake.random_int(1, 5)
    home_delivery = fake.boolean()
    return (
        items,
        home_delivery,
        fake.date_time_between(start_date="-1w", end_date="now").timestamp(),
    )

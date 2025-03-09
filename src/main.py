from cli import loop, Context
from database import FileSystemStore


def main():
    store = FileSystemStore("pizza.json")
    context = Context(store)
    loop(context)
    store.save()


if __name__ == "__main__":
    main()

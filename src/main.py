from cli import loop, Context
from database import FileSystemStore


def main():
    # instantiate a FileSystemStore and a Context object to run the command line interface
    store = FileSystemStore("pizza.json")
    context = Context(store)
    # blocks until the user exits the program
    loop(context)
    # and saves if not already saved
    store.save()


if __name__ == "__main__":
    main()

"""Local mosaicking from commanded stage positions."""


def main():
    from .scan import run_scan
    run_scan(regression=False)


if __name__ == "__main__":
    main()

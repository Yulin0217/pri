"""Preview screen rectangles without importing or opening the robot SDK."""


def main():
    import cv2

    from smarpod_pcle.screen_capture import capture_partial_screen

    try:
        while True:
            left = input("Left screen coordinate (q to quit): ").strip()
            if left.lower() == "q":
                break
            try:
                rectangle = {
                    "left": int(left),
                    "top": int(input("Top screen coordinate: ")),
                    "width": int(input("Width (pixels): ")),
                    "height": int(input("Height (pixels): ")),
                }
                if rectangle["width"] <= 0 or rectangle["height"] <= 0:
                    raise ValueError("Width and height must be positive")
            except ValueError as error:
                print(f"Invalid rectangle: {error}")
                continue
            image = capture_partial_screen(**rectangle)
            print("Copy these values into [capture.pcle_view] or [capture.mosaic_view]:")
            for key, value in rectangle.items():
                print(f"{key} = {value}")
            cv2.imshow("Captured screen region — press any key to close", image)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

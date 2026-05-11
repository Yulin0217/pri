# Before Initialization
1. Find the USB locater by `smarpod.FindSystems()`.
2. Define the right model code. For example, model code is 10001. You need to configure controller by `smarpod.ConfigureController(10001, locator)`.
3. Initialization by `smarpod.Open(10001, locator)`
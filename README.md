# Python Serial Debug Monitor

This is a Serial Monitor written in Python.

This program by itself is not very different from many other serial monitor programs. It has been intentionally kept simple with a very open (MIT) license so that it can be taken apart and reused in other applications.

<!-- A .wxg file is also included in this repository which can be loaded and modified using WxGlade a very simple python GUI builder for WxPython. -->

![alt text](https://raw.githubusercontent.com/brainelectronics/SerialDebugMonitor/master/images/serial_monitor.png)

## Installation

1. Clone the repository:

```bash
git clone https://github.com/brainelectronics/SerialDebugMonitor.git
```

2. You may need wx widgets for python.

On Linux use this:
```bash
apt-get install python-wxgtk2.8
```

On Windows or Mac use pip:
```bash
pip install -U wxPython
```

Or folow the directions here: https://wiki.wxpython.org/How%20to%20install%20wxPython

3. To run the code you simply use:

```bash
python serialDebugMonitor.py
```

4. Since this program accesses COM ports you may increased privlidges to use this program. In Ubuntu you can create new rules for a specific device (recommended) or run as admin (not recommended).

## Authors

* **brainelectronics** - *JSON Decoder* - [brainelectronics](https://github.com/brainelectronics/SerialDebugMonitor)
* **Lesley Gushurst** - *Initial work* - [Volunteer Research Laboratories LLC](https://github.com/volunteerlabs/PythonSerialMonitor)

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details

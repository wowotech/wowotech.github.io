---
title: "X-024-OHTHERS-在windows平台下使用libusb"
date: 2017-07-23T22:21:15+08:00
url: "/x_project/libusb_on_windows.html"
gid: "403"
emlog_type: "blog"
summary: "\n\t话说我们“X Project”的第一个任务就是通过USB将主机上的Image文件下载到开发板的Ram中执行（参考[1]中有关的内容），为此我们在host中porting了一个简单的应用程序（称作DFU[2]），负责和开发板ROM中的代码交流，下载并执行Image文件。为了方便，该应用程序使用libusb[3]进行USB有关的操作。\n\n\n\tlibusb不止使用起来简单，还有一个极大的优点，就是“"
author: "wowo"
category: "X Project"
category_alias: "x_project"
tags: ["MinGW", "libusb", "windows", "zadig", "dfu"]
views: 21820
comment_count: 1
aliases:
  - "/x_project/403.html"
  - "/403.html"
---

## 1. 前言

话说我们“[X Project](/sort/x_project)”的第一个任务就是通过USB将主机上的Image文件下载到开发板的Ram中执行（参考[1]中有关的内容），为此我们在host中porting了一个简单的应用程序（称作DFU[2]），负责和开发板ROM中的代码交流，下载并执行Image文件。为了方便，该应用程序使用libusb[3]进行USB有关的操作。

libusb不止使用起来简单，还有一个极大的优点，就是“跨平台”的特性。我们之前的例子[4]都是在Linux平台下操作的，最近由于win10内置了Ubuntu，Linux平台有关的开发工作，基本上都可以在这里完成了，因此就不需要费时、费神地切换到纯Linux环境下工作了。

不过呢，Win10的Ubuntu好是好，但没法像纯Linux系统那样支持USB设备，DFU有关的工作就无法在这里正常工作，因此就发挥libusb的特性，把“[X Project](/sort/x_project)” DFU[2]有关的代码在Windows下跑起来，也算感受一下“跨平台”的魅力。具体步骤如下。

## 2. 步骤

1）安装MinGW[6]

参考[5]中的介绍，libusb在Windows下可以在MinGW环境下编译、使用，因此我们可以按照[7]中的步骤，在Windows中下载并安装MinGW。

2） 编译libusb、dfu，并运行dfu（具体可参考[1]中有关的文章）

发现没有USB的驱动程序（见下面的log）：

> cd /d/work/xprj/build && make libusb && make dfu   
>   
> cd /d/work/xprj/tools/dfu && ./dfu.exe bubblegum 0   
> board\_bubblegum\_init   
> board bubblegum   
> address 0x0   
> filename (null)   
> need\_run 0   
> bubblegum\_init   
> b96\_init\_usb   
> b96\_init\_device   
> libusb: info [windows\_get\_device\_list] The following device has no driver: '\\.\USB#VID\_10D6&PID\_10D6#5&A3E6D0F&0&3'   
> libusb: info [windows\_get\_device\_list] libusb will not be able to access it.   
> Error: cannot open device 10d6:10d6   
> b96\_init\_device failed   
> board->init failed!

3）通过Zadig[8]安装USB的通用驱动

参考[5]中的说明，要在Windows访问USB设备，需要相应的驱动程序，例如WinUSB等，可以使用Zadig[8]工具辅助安装：

> ##### [https://github.com/libusb/libusb/wiki/Windows#How\_to\_use\_libusb\_on\_Windows](https://github.com/libusb/libusb/wiki/Windows#How_to_use_libusb_on_Windows "https://github.com/libusb/libusb/wiki/Windows#How_to_use_libusb_on_Windows") Driver Installation
>
> If your target device is not HID, you **must** install a driver before you can communicate with it using libusb. Currently, this means installing one of Microsoft's `WinUSB`, [libusb-win32](http://sourceforge.net/apps/trac/libusb-win32/wiki) or [libusbK](http://libusbk.sourceforge.net/UsbK3/index.html) drivers. Two options are available:
>
> - **Recommended**: Use the most recent version of **[Zadig](http://zadig.akeo.ie/)**, an Automated Driver Installer GUI application for `WinUSB`, `libusb-win32` and `libusbK`...
> - Alternatively, if you are only interested in `WinUSB`, you can download the [WinUSB driver files](https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/libusb-winusb-wip/winusb%20driver.zip) and customize the `inf` file for your device.

> [http://zadig.akeo.ie/](http://zadig.akeo.ie/ "http://zadig.akeo.ie/")  
>  ***Zadig*** is a Windows application that installs generic USB drivers, such as [WinUSB](http://msdn.microsoft.com/en-us/library/windows/hardware/ff540174.aspx), [libusb-win32/libusb0.sys](http://sourceforge.net/apps/trac/libusb-win32/wiki) or [libusbK](http://code.google.com/p/usb-travis/), to help you access USB devices.

Zadig的使用极其简单，通过USB ID确定需要安装驱动的USB设备，然后再右边的列表中选择安装的驱动类型（这里以WinUSB为例），点击“Install Driver”即可，如下图所示：

[![image](/content/uploadfile/201707/fc14b80aa29aafc174432f4167535e9e20170723142114.png "image")](/content/uploadfile/201707/b085b16f660d3bf0e9b640e276d01ac720170723142053.png)

4）再次运行dfu工具，已经和开发板对上暗号了，成功！！

> $ /d/work/xprj/build/../tools/dfu/dfu bubblegum 0xe406b200 /d/work/xprj/build/../tools/actions/splboot.bin 1   
> board\_bubblegum\_init   
> board bubblegum   
> address 0xe406b200   
> filename d:/work/xprj/build/../tools/actions/splboot.bin   
> need\_run 1   
> bubblegum\_init   
> b96\_init\_usb   
> b96\_init\_device   
> bDescriptorType: 1   
> bNumConfigurations: 1   
> iManufacturer: 0   
> bNumInterfaces: 1   
> Info: cannot detach kernel driver: LIBUSB\_ERROR\_NOT\_SUPPORTED   
> Configuiration: 1   
> Handler: 009AB270   
> bubblegum\_upload, filename d:/work/xprj/build/../tools/actions/splboot.bin, addr 0xe406b200   
> writeBinaryFile   
> writeBinaryFileSeek   
> CBW: 55 53 42 43 00 00 00 00 83 43 00 00 00 00 10 05 00 b2 06 e4 83 43 00 00 00 00 00 00 00 00 00   
> Bulk transferred 17283 bytes   
> readCSW   
> CSW:55 53 42 53 00 00 00 00 00 00 00 00 00   
> bubblegum\_run, addr 0xe406b200   
> unknownCMD07   
> CBW: 55 53 42 43 00 00 00 00 00 00 00 00 00 00 00 10 00 b2 06 e4 00 00 00 00 00 00 00 00 00 00 00   
> Transffered: 31   
> readCSW   
> CSW:55 53 42 53 00 00 00 00 00 00 00 00 00   
> bubblegum\_exit   
> b96\_uninit\_device   
> b96\_uninit\_usb

## 3. 参考文档

[1] [【任务1】启动过程-Boot from USB](/forum/15.html)

[2] xprj dfu, [https://github.com/wowotechX/tools/tree/master/dfu](https://github.com/wowotechX/tools/tree/master/dfu "https://github.com/wowotechX/tools/tree/master/dfu")

[3] libusb, [http://libusb.info/](http://libusb.info/ "http://libusb.info/")

[4] [X-010-UBOOT-使用booti命令启动kernel(Bubblegum-96平台)](/x_project/bubblegum_uboot_booti.html)

[5] [https://github.com/libusb/libusb/wiki/Windows#How\_to\_use\_libusb\_on\_Windows](https://github.com/libusb/libusb/wiki/Windows#How_to_use_libusb_on_Windows "https://github.com/libusb/libusb/wiki/Windows#How_to_use_libusb_on_Windows")

[6] MinGW, [www.mingw.org/](http://www.mingw.org/ "http://www.mingw.org/")

[7] [Windows系统结合MinGW搭建软件开发环境](/soft/6.html)

[8] zadig, [http://zadig.akeo.ie/](http://zadig.akeo.ie/ "http://zadig.akeo.ie/")

[9] [X-002-HW-S900芯片boot from USB有关的硬件描述](/x_project/s900_hw_adfu.html)

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/x_project/libusb_on_windows.html)。

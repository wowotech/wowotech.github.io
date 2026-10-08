---
title: "Linux TTY framework(4)_TTY driver"
date: 2016-10-25T22:40:31+08:00
url: "/tty_framework/tty_driver.html"
gid: "344"
emlog_type: "blog"
summary: "\r\n\t本文将从驱动工程师的角度去看TTY framework：它怎么抽象、管理各个TTY设备？它提供了哪些编程接口以方便TTY driver的开发？怎么利用这些接口编写一个TTY driver？等等。\r\n\r\n\r\n\t注1：话说介绍各个framework的时候，我一直比较喜欢用provider、consumer等概念，因为非常生动、易懂。不过在TTY framework的官方俗语中，压根没有provi"
author: "wowo"
category: "TTY子系统"
category_alias: "tty_framework"
tags: ["Linux", "Kernel", "内核", "driver", "tty", "tty_struct", "tty_port"]
views: 22287
comment_count: 13
aliases:
  - "/tty_framework/344.html"
  - "/344.html"
---

## 1. 前言

本文将从驱动工程师的角度去看TTY framework：它怎么抽象、管理各个TTY设备？它提供了哪些编程接口以方便TTY driver的开发？怎么利用这些接口编写一个TTY driver？等等。

注1：话说介绍各个framework的时候，我一直比较喜欢用provider、consumer等概念，因为非常生动、易懂。不过在TTY framework的官方俗语中，压根没有provider、consumer等概念，为了不混淆试听，就算了吧。

注2：TTY framework在Linux kernel中算得上一个比较繁琐、庞杂的framework了，再加上现在很少有人会直接去写一个TTY driver，因此本文只是介绍一些概念性的东西，以加深对TTY及其driver的理解，为后续学习serial framework打基础。一些细节的东西，大家可参考[callme\_friend](/author/148)同学写的"[TTY驱动分析](/forum/183.html)[2]”，特别是其中的一些图示，很清晰！

注3：本文所使用的kernel版本为“[X Project](/forum/)”初始的“[Linux 4.6-rc5](https://github.com/wowotechX/linux/tree/02da2d72174c61988eb4456b53f405e3ebdebce4)”版本。

## 2. 关键数据结构

注4：阅读本章内容时可对照[callme\_friend](/author/148)画的的TTY个数据结构的关系图[3]以加深理解。

#### 2.1 TTY device

Linux TTY framework的核心功能，就是管理TTY设备，以方便应用程序使用。于是，问题来了，Linux kernel是怎么抽象TTY设备的呢？答案很尴尬，kernel并不认为TTY device是一个设备，这很好理解：

> 比如，我们熟悉的串口终端，串口控制器（serial controller）是一个实实在在的硬件设备，一个控制器可以支持多个串口（serial port），软件在串口上收发数据，就相当于在驱动“串口终端”。此处的TTY device，就是从串口控制器中抽象出来的一个数据通道；
>
> 再比如，我们常用的网络终端，只有以太网控制器（或者WLAN控制器）是实实在在的设备，sshd等服务进程，会基于网络socket，虚拟出来一个数据通道，软件在这个通道上收发数据，就相当于在驱动“网络终端”。

因此，从kernel的角度看，TTY device就是指那些“虚拟的数据通道”。

另外，由于TTY driver在linux kernel中出现的远比设备模型早，所以在TTY framework中，没有特殊的数据结构用于表示TTY设备。当然，为了方便，kernel从设备模型和字符设备两个角度对它进行了抽象：

1）设备模型的角度

为每个“数据通道”注册了一个stuct device，以便可以在sysfs中体现出来，例如：

> /sys/class/tty/tty
>
> /sys/class/tty/console
>
> /sys/class/tty/ttyS0

2）字符设备的角度

为每个“数据通道”注册一个struct cdev，以便在用户空间可以访问，例如：

> /dev/tty
>
> /dev/console
>
> /dev/ttyS0

## 2.2 TTY driver

从当前设备模型的角度看，TTY framework有点奇怪，它淡化了device的概念（参考2.1的介绍），却着重突出driver。由struct tty\_driver所代表的TTY driver，几乎大包大揽了TTY device有关的所有内容，如下：

> struct tty\_driver {   
> int magic; /\* magic number for this structure \*/   
> struct kref kref; /\* Reference management \*/   
> struct cdev \*\*cdevs;   
> struct module \*owner;   
> const char \*driver\_name;   
> const char \*name;   
> int name\_base; /\* offset of printed name \*/   
> int major; /\* major device number \*/   
> int minor\_start; /\* start of minor device number \*/   
> unsigned int num; /\* number of devices allocated \*/   
> short type; /\* type of tty driver \*/   
> short subtype; /\* subtype of tty driver \*/   
> struct ktermios init\_termios; /\* Initial termios \*/   
> unsigned long flags; /\* tty driver flags \*/   
> struct proc\_dir\_entry \*proc\_entry; /\* /proc fs entry \*/   
> struct tty\_driver \*other; /\* only used for the PTY driver \*/
>
> /\*   
> \* Pointer to the tty data structures   
> \*/   
> struct tty\_struct \*\*ttys;   
> struct tty\_port \*\*ports;   
> struct ktermios \*\*termios;   
> void \*driver\_state;
>
> /\*   
> \* Driver methods   
> \*/
>
> const struct tty\_operations \*ops;   
> struct list\_head tty\_drivers;   
> }

原则上来说，在编写TTY driver的时候，我们只需要定义一个struct tty\_driver变量，并根据实际情况正确填充其中的字段后，注册到TTY core中，即可完成驱动的设计。当然，我们不需要关心struct tty\_driver中的所有字段，下面我们捡一些重点的字段一一说明。

1）需要TTY driver关心的字段

> driver\_name，该TTY driver的名称，在软件内部使用；
>
> name，该TTY driver所驱动的TTY devices的名称，会体现到sysfs以及/dev/等文件系统下；
>
> major、minor\_start，该TTY driver所驱动的TTY devices的在字符设备中的主次设备号。因为一个tty driver可以支持多个tty device，因此次设备号只指定了一个start number；
>
> num，该driver所驱动的tty device的个数，可以在tty driver注册的时候指定，也可以让TTY core自行维护，具体由TTY\_DRIVER\_DYNAMIC\_DEV flag决定（可参考“”中的介绍）；
>
> type、subtype，TTY driver的类型，具体可参考“include/linux/tty\_driver.h”中的定义；
>
> init\_termios，初始的termios，可参考2.5小节的介绍；
>
> flags，可参考2.6小节的介绍；
>
> ops，tty driver的操作函数集，可参考2.7小节的介绍；
>
> driver\_state，可存放tty driver的私有数据。

2）内部使用的字段

> ttys，一个struct tty\_struct类型的指针数组，可参考2.3小节的介绍；
>
> ports，一个struct tty\_port类型的指针数组，可参考2.4小节的介绍；
>
> termios，一个struct ktermios类型的指针数组，可参考2.5小节的介绍。

#### 2.3 TTY struct(struct tty\_struct)

TTY struct是TTY设备在TTY core中的内部表示。

从TTY driver的角度看，它和文件句柄的功能类似，用于指代某个TTY设备。

从TTY core的角度看，它是一个比较复杂的数据结构，保存了TTY设备生命周期中的很多中间变量，如：

> dev，该设备的struct device指针；
>
> driver，该设备的struct tty\_driver指针；
>
> ops，该设备的tty操作函数集指针；
>
> index，该设备的编号（如tty0、tty1中的0、1）；
>
> 一些用于同步操作的mutex锁、spinlock锁、读写信号量等；
>
> 一些等待队列；
>
> write buffer有关的信息；
>
> port，该设备对应的struct tty\_port（可参考2.4小节的介绍）
>
> 等等。

由于编写TTY driver的时候不需要特别关心struct tty\_struct的内部细节，这里不再详细介绍。

#### 2.4 TTY port(struct tty\_port)

在TTY framework中TTY port是一个比较难理解的概念，因为它和TTY struct类似，也是TTY device的一种抽象。那么，既然有了TTY struct，为什么还需要TTY port呢？先看一下kernel代码注释的解释：

> /\* include/linux/tty.h \*/
>
> /\*   
> \* Port level information. Each device keeps its own port level information   
> \* so provide a common structure for those ports wanting to use common support   
> \* routines.   
> \*   
> \* The tty port has a different lifetime to the tty so must be kept apart.   
> \* In addition be careful as tty -> port mappings are valid for the life   
> \* of the tty object but in many cases port -> tty mappings are valid only   
> \* until a hangup so don't use the wrong path.   
> \*/

我的理解是：

> TTY struct是TTY设备的“动态抽象”，保存了TTY设备访问过程中的一些临时信息，这些信息是有生命周期的：从打开TTY设备开始，到关闭TTY设备结束；
>
> TTY port是TTY设备固有属性的“静态抽象”，保存了该设备的一些固定不变的属性值，例如是否是一个控制台设备（console）、打开关闭时是否需要一些delay操作、等等；
>
> 另外（这一点很重要），TTY core负责的是逻辑上的抽象，并不关心这些固有属性。因此从层次上看，这些属性完全可以由具体的TTY driver自行维护；
>
> 不过，由于不同TTY设备的属性有很多共性，如果每个TTY driver都维护一个私有的数据结构，将带来代码的冗余。所以TTY framework就将这些共同的属性抽象出来，保存在struct tty\_port数据结构中，同时提供一些通用的操作接口，供具体的TTY driver使用；
>
> 因此，总结来说：TTY struct是TTY core的一个数据结构，由TTY core提供并使用，必要的时候可以借给具体的TTY driver使用；TTY port是TTY driver的一个数据结构，由TTY core提供，由具体的TTY driver使用，TTY core完全不关心。

#### 2.5 termios(struct ktermios)

说实话，在Unix/Linux的世界中，终端（terminal）编程是一个非常繁琐的事情，为了改善这种状态，特意制订了符合POSIX规范的应用程序编程接口，称作POSIX terminal interface[3]。POSIX terminal interface操作的对象，就是名称为termios的数据结构（在用户空间为struct termios，内核空间为struct ktermios）。以kernel中的struct ktermios为例，其定义如下：

> /\* include/uapi/asm-generic/termbits.h \*/
>
> struct ktermios {   
> tcflag\_t c\_iflag; /\* input mode flags \*/   
> tcflag\_t c\_oflag; /\* output mode flags \*/   
> tcflag\_t c\_cflag; /\* control mode flags \*/   
> tcflag\_t c\_lflag; /\* local mode flags \*/   
> cc\_t c\_line; /\* line discipline \*/   
> cc\_t c\_cc[NCCS]; /\* control characters \*/   
> speed\_t c\_ispeed; /\* input speed \*/   
> speed\_t c\_ospeed; /\* output speed \*/   
> };

说实话，要理解上面的数据结构，真的不是一件容易的事情，这里只能简单介绍一些我们常用的内容，更为具体的，如有需要，后面会用单独的文章去分析：

> c\_cflag，可以控制TTY设备的一些特性，例如data bits、parity type、stop bit、flow control等（例如串口设备中经常提到的8N1）；
>
> c\_ispeed、c\_ospeed，可以分别控制TTY设备输入和输出的速度（例如串口设备中的波特率）；
>
> 其它，暂不介绍。

#### 2.6 tty driver flags

TTY driver在注册struct tty\_driver变量的时候，可以提供一些flags，以告知TTY core一些额外的信息，例如（具体可参考include/linux/tty\_driver.h中的定义和注释，写的很清楚）：

> TTY\_DRIVER\_DYNAMIC\_DEV：如果设置了该flag，则表示TTY driver会在需要的时候，自行调用tty\_register\_device接口注册TTY设备（相应地回体现在字符设备以及sysfs中）；如果没有设置，TTY core会在tty\_register\_driver时根据driver->num信息，自行创建对应的TTY设备。

#### 2.7 TTY操作函数集

TTY core将和硬件有关的操作，抽象、封装出来，形成名称为struct tty\_operations的数据结构，具体的TTY driver不需要关心具体的业务逻辑，只需要根据实际的硬件情况，实现这些操作接口即可。

听着还挺不错啊（framework的中心思想一贯如此，大家牢记即可），不过不能高兴的太早，看过这个数据结构之后，估计心会凉半截：

> struct tty\_operations {   
> struct tty\_struct \* (\*lookup)(struct tty\_driver \*driver,   
> struct inode \*inode, int idx);   
> int (\*install)(struct tty\_driver \*driver, struct tty\_struct \*tty);   
> void (\*remove)(struct tty\_driver \*driver, struct tty\_struct \*tty);   
> int (\*open)(struct tty\_struct \* tty, struct file \* filp);   
> void (\*close)(struct tty\_struct \* tty, struct file \* filp);   
> void (\*shutdown)(struct tty\_struct \*tty);   
> void (\*cleanup)(struct tty\_struct \*tty);   
> int (\*write)(struct tty\_struct \* tty,   
> const unsigned char \*buf, int count);   
> int (\*put\_char)(struct tty\_struct \*tty, unsigned char ch);   
> void (\*flush\_chars)(struct tty\_struct \*tty);   
> int (\*write\_room)(struct tty\_struct \*tty);   
> int (\*chars\_in\_buffer)(struct tty\_struct \*tty);   
> int (\*ioctl)(struct tty\_struct \*tty,   
> unsigned int cmd, unsigned long arg);   
> long (\*compat\_ioctl)(struct tty\_struct \*tty,   
> unsigned int cmd, unsigned long arg);   
> void (\*set\_termios)(struct tty\_struct \*tty, struct ktermios \* old);   
> void (\*throttle)(struct tty\_struct \* tty);   
> void (\*unthrottle)(struct tty\_struct \* tty);   
> void (\*stop)(struct tty\_struct \*tty);   
> void (\*start)(struct tty\_struct \*tty);   
> void (\*hangup)(struct tty\_struct \*tty);   
> int (\*break\_ctl)(struct tty\_struct \*tty, int state);   
> void (\*flush\_buffer)(struct tty\_struct \*tty);   
> void (\*set\_ldisc)(struct tty\_struct \*tty);   
> void (\*wait\_until\_sent)(struct tty\_struct \*tty, int timeout);   
> void (\*send\_xchar)(struct tty\_struct \*tty, char ch);   
> int (\*tiocmget)(struct tty\_struct \*tty);   
> int (\*tiocmset)(struct tty\_struct \*tty,   
> unsigned int set, unsigned int clear);
>
> int (\*resize)(struct tty\_struct \*tty, struct winsize \*ws);   
> int (\*set\_termiox)(struct tty\_struct \*tty, struct termiox \*tnew);   
> int (\*get\_icount)(struct tty\_struct \*tty,   
> struct serial\_icounter\_struct \*icount);   
> #ifdef CONFIG\_CONSOLE\_POLL   
> int (\*poll\_init)(struct tty\_driver \*driver, int line, char \*options);   
> int (\*poll\_get\_char)(struct tty\_driver \*driver, int line);   
> void (\*poll\_put\_char)(struct tty\_driver \*driver, int line, char ch);   
> #endif   
> const struct file\_operations \*proc\_fops;   
> };

这也太复杂了吧？确实如此，好在终端设备正在慢慢的退出历史舞台，看这篇文章的同学们，可能这一辈子都不会直接去写一个TTY driver。所以，这里我也不打算详细介绍，仅仅出于理解TTY framework的目的，做如下说明：

> 这些操作函数的操作对象，基本上都是struct tty\_struct类型的指针，这也印证了我们在2.3中所说的----TTY struct是TTY设备的操作句柄；
>
> 当然，具体的TTY driver，可以从struct tty\_struct指针中获取足够多的有关该TTY设备的信息，例如TTY port等；
>
> TTY core会通过“.write“接口，将输出信息送给终端设备并显示。因此具体的TTY driver需要实现该接口，并通过硬件操作将数据送出；
>
> 你一定会好奇：既然有“.write“接口，为什么没有相应的read接口？TTY设备上的输入信息，怎么经由TTY core送给Application呢？具体可以参考"[TTY驱动分析](/forum/183.html)[2]”，本文不再详细介绍了。

## 3. 提供的用于编写TTY driver的API

在提供了一系列的数据结构的同时，TTY framework向下封装了一些API，以方便TTY driver的开发，具体如下。

#### 3.1 TTY driver有关的API

用于struct tty\_driver数据结构的分配、初始化、注册等：

> /\* include/linux/tty\_driver.h \*/
>
> extern struct tty\_driver \*\_\_tty\_alloc\_driver(unsigned int lines,   
> struct module \*owner, unsigned long flags);   
> extern void put\_tty\_driver(struct tty\_driver \*driver);   
> extern void tty\_set\_operations(struct tty\_driver \*driver,   
> const struct tty\_operations \*op);   
> extern struct tty\_driver \*tty\_find\_polling\_driver(char \*name, int \*line);
>
> extern void tty\_driver\_kref\_put(struct tty\_driver \*driver);
>
> /\* Use TTY\_DRIVER\_\* flags below \*/   
> #define tty\_alloc\_driver(lines, flags) \   
> \_\_tty\_alloc\_driver(lines, THIS\_MODULE, flags)

> /\* include/linux/tty.h \*/
>
> extern int tty\_register\_driver(struct tty\_driver \*driver);   
> extern int tty\_unregister\_driver(struct tty\_driver \*driver);

tty\_alloc\_driver，分配一个struct tty\_driver指针，并初始化那些不需要driver关心的字段：

> lines，指明该driver最多能支持多少个设备，TTY core会根据该参数，分配相应个数的ttys、ports、termios数组；
>
> flags，请参考2.6小节的说明。

tty\_set\_operations，设置TTY操作函数集。

tty\_register\_driver，将TTY driver注册给TTY core。

#### 3.2 TTY device有关的API

如果TTY driver设置了TTY\_DRIVER\_DYNAMIC\_DEV flag，就需要自行注册TTY device，相应的API包括：

> /\* include/linux/tty.h \*/
>
> extern struct device \*tty\_register\_device(struct tty\_driver \*driver,   
> unsigned index, struct device \*dev);   
> extern struct device \*tty\_register\_device\_attr(struct tty\_driver \*driver,   
> unsigned index, struct device \*device,   
> void \*drvdata,   
> const struct attribute\_group \*\*attr\_grp);   
> extern void tty\_unregister\_device(struct tty\_driver \*driver, unsigned index);

tty\_register\_device，分配并注册一个TTY device，最后将新分配的设备指针返回给调用者：

> driver，对应的TTY driver；
>
> index，该TTY设备的编号，它会决定该设备在字符设备中的设备号，以及相应的设备名称，例如/dev/ttyS0中的‘0’；
>
> dev，可选的父设备指针。

tty\_register\_device\_attr，和tty\_register\_device类似，只不过可以额外指定设备的attribute。

#### 3.3 数据传输有关的API

当TTY core有数据需要发送给TTY设备时，会调用TTY driver提供的.write或者.put\_char回调函数，TTY driver在这些回调函数中操作硬件即可。

当TTY driver从TTY设备收到数据并需要转交给TTY core的时候，需要调用TTY buffer有关的接口，将数据保存在缓冲区中，并等待Application读取，相关的API有：

> /\* include/linux/tty\_flip.h \*/
>
> static inline int tty\_insert\_flip\_char(struct tty\_port \*port,   
> unsigned char ch, char flag)   
> {   
> ….   
> }
>
> static inline int tty\_insert\_flip\_string(struct tty\_port \*port,   
> const unsigned char \*chars, size\_t size)   
> {   
> return tty\_insert\_flip\_string\_fixed\_flag(port, chars, TTY\_NORMAL, size);   
> }

注5：本文没有涉及TTY buffer、TTY flip有关的知识，大家知道有这么回事就行了。

## 4. TTY driver的编写步骤

说实话，TTY driver的编写步骤，就和“把大象放进冰箱”一样“简单”：

> 步骤1：实现TTY设备有关的操作函数集，并保存在一个struct tty\_operations变量中。
>
> 步骤2：调用tty\_alloc\_driver分配一个TTY driver，并根据实际情况，设置driver中的字段（包括步骤1中的struct tty\_operations变量）。
>
> 步骤3：调用tty\_register\_driver将driver注册到kernel。
>
> 步骤4：如果需要动态注册TTY设备，在合适的时机，调用tty\_register\_device或者tty\_register\_device\_attr，向kernel注册TTY设备。
>
> 步骤5：接收到数据时，调用tty\_insert\_flip\_string或者tty\_insert\_flip\_char将数据交给TTY core；TTY core需要发送数据时，会调用driver提供的回调函数，在那里面访问硬件送出数据即可。

好吧，相信任何人看到上面的步骤之后，都没办法去写一个完整的TTY driver（我也是）。好在这是一个幸福的时代，我们很少需要直接去写这样的一个driver。那么本文的目的又是什么呢？权当是一个科普吧，如果你真的打算去写一个TTY driver，不至于无从下手。

## 5. 参考文档

[1] [Linux TTY framework(2)\_软件架构](/tty_framework/tty_architecture.html)

[2] TTY驱动分析（链接失效，TODO）

[3] TTY各数据结构关系图，/content/uploadfile/201505/eb451430746679.gif（（链接失效，TODO））

[4] POSIX terminal interface，[https://en.wikipedia.org/wiki/POSIX\_terminal\_interface#CITEREFZlotnick1991](https://en.wikipedia.org/wiki/POSIX_terminal_interface#CITEREFZlotnick1991 "https://en.wikipedia.org/wiki/POSIX_terminal_interface#CITEREFZlotnick1991")

[5] [Linux设备模型(4)\_sysfs](/device_model/dm_sysfs.html)

*原创文章，转发请注明出处。蜗窝科技*，[www.wowotech.net](/tty_framework/tty_driver.html)。

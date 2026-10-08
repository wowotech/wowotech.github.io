---
title: "Linux serial framework(1)_概述"
date: 2016-12-12T22:04:41+08:00
url: "/comm/serial_overview.html"
gid: "363"
emlog_type: "blog"
summary: "\r\n\t串口设备（serial or uart，后面不再区分）是TTY设备的一种，Linux kernel为了方便串口驱动的开发，在TTY \r\nframework的基础上，封装了一层串口框架（serial \r\nframework）。该框架尽可能的屏蔽了TTY有关的技术细节（比较难懂），驱动工程师在编写串口驱动的时候，只需要把精力放在串口以及串口控制器本身即可。\r\n\r\n\r\n\t本文将通过对serial "
author: "wowo"
category: "通信类协议"
category_alias: "comm"
tags: ["Linux", "driver", "framework", "serial", "框架", "串口"]
views: 19535
comment_count: 10
aliases:
  - "/comm/363.html"
  - "/363.html"
---

## 1. 前言

串口设备（serial or uart，后面不再区分）是TTY设备的一种，Linux kernel为了方便串口驱动的开发，在TTY framework的基础上，封装了一层串口框架（serial framework）。该框架尽可能的屏蔽了TTY有关的技术细节（比较难懂），驱动工程师在编写串口驱动的时候，只需要把精力放在串口以及串口控制器本身即可。

本文将通过对serial framework的简单分析，理解上面的概念，并掌握基于该框架编写串口驱动的方法和步骤。

## 2. 软件架构

Linux kernel serial framework位于“drivers/tty/serial”目录中，其软件架构（如下面图片1所示）比较简单：

[![serial_framework_arch](/content/uploadfile/201612/a1c90c3e81c89c1a391bf9124974146020161212140441.gif "serial_framework_arch")](/content/uploadfile/201612/311d29b8613c8a1b76eb58a3ae3842bb20161212140440.gif)

图片1 Serial framework软件架构

Serial core是Serial framework的核心实现，对上封装、屏蔽TTY的技术细节，对下为具体的串口驱动提供简单、统一的编程API。

earlycon（early console）是serial framework中比较新的一个功能，它基于Kernel system console的框架，提供了一种比较简单的控制台实现方式。

最后就是具体的串口驱动（Serial drivers）了，不再详细介绍。

## 3. serial core

#### 3.1 功能介绍

serial core主要实现如下三类功能（任何一个framework的core模块都提供类似的功能，这就是套路！~）：

> 1）将串口设备有关的物理对象（及其操作方法）封装成一个一个的数据结构，以达到用软件语言描述硬件的目的。
>
> 2）向底层driver提供串口驱动的编程接口。
>
> 3）基于TTY framework所提供的TTY driver的编写规则，将底层driver看到的serial driver，转换为TTY driver，并将所有的serial操作，转换为对应的tty操作。

本文将重点介绍1）和2）两类功能，第3）类，属于TTY core的内部逻辑，由于比较简单就不多说了。

#### 3.2 关键数据结构

数据结构是一个软件模块的灵魂和骨架，而对设备驱动来说，数据结构一般和具体的硬件实体对应，例如：

> 假如一个soc中有5个串口控制器（也可称作uart控制器，后面我们不再区分），每个uart控制器都可引出一个串口（uart port）。那么：
>
> 每个uart控制器，都是一个platform device，它们可由同一个patform driver驱动；
>
> 相对于uart控制器实实在在的存在，我们更为熟悉的串口（uart port），可以看作虚拟的设备，serial core将它们抽象为“struct uart\_port”，并在platform driver的probe接口中，注册到kernel；
>
> 和platform device类似，这些虚拟的串口设备，也可由同一个虚拟的driver驱动，这就是serial core中的“struct uart\_driver”。

下面我们将跟随上面的思路，介绍serial core提供的数据结构（具体可参考“include/linux/serial\_core.h”）。

**3.2.1 struct uart\_port**

在serial framework中，struct uart\_port抽象虚拟的串口设备（具体的串口控制器，则为实实在在的硬件设备），这是一个庞大的数据结构，存放了五花八门的、各式各样的、有新有旧的、有用没有的和串口设备有关的信息，例如（不能全部罗列，大家在写driver的时候，可以有事没事去看看，说不定就有惊喜）：

1）最基本、最必须的，需要驱动工程师根据实际的硬件自行填充的字段

> dev，父设备的指针，通常是串口控制器所对应的platform device；
>
> type，该串口的类型，是以PORT\_为前缀的一个宏定义，可以根据需要在include/uapi/linux/serial\_core.h中定义；
>
> ops，该串口的操作函数集（struct uart\_ops类型的指针），具体可参考3.2.3；
>
> iotype，该串口的I/O类型，例如UPIO\_MEM32（常用的通过寄存器访问的uart控制器）；
>
> mapbase，对应MEM类型的串口，保存它的寄存器基址（物理地址），一般是从DTS中解析得到的
>
> membase，从mapbase ioremap得来（虚拟地址）；
>
> irq、irqflags，该串口对应的中断号（以及相应的终端flags）， 一般是从DTS中解析得到的；
>
> line，该串口的编号，和字符设备的次设备号等有关。

2）和运行时状态有关的字段

> lock，一个自旋锁（spinlock\_t类型），用于对该数据结构进行访问保护；
>
> icount，一个struct uart\_icount类型变量，用于保存该串口的统计信息，例如收发数据的统计等；
>
> cons，console指针，如果该串口被注册为system console的话，将对应的console指针保存在这里；
>
> state，struct uart\_state指针，具体请参考3.2.2。

3）一些有用的函数指针（driver实现，serial core调用），例如

> serial\_in，读取该串口的某个寄存器；
>
> serial\_out，向该串口的某个寄存器写入某一value；
>
> 最后，serial core根据这两个函数指针，封装出两个公共的寄存器访问接口：serial\_port\_in和serial\_port\_out，以方便driver使用。

注1：struct uart\_port中的内容非常多，因此在编写串口驱动的时候，要把握一个原则：不到万不得已的时候，不要新定义变量，多去struct uart\_port找找，很有可能就找到了你想要的东西。

**3.2.2 struct uart\_state**

struct uart\_state中保存了串口使用过程中的动态信息（它们的生命周期是串口被打开到被关闭的过程），包括：

> port，对应的struct tty\_port变量（uart port是tty port的一个特例）；
>
> pm\_state，电源管理有关的状态，例如UART\_PM\_STATE\_ON、UART\_PM\_STATE\_OFF和UART\_PM\_STATE\_UNDEFINED三种；
>
> xmit，用于保存TX数据的环形缓冲区（struct circ\_buf，具体可参考include/linux/circ\_buf.h）；
>
> uart\_port，struct uart\_port类型的指针，指向所属的串口。

**3.2.3 struct uart\_ops**

使用struct uart\_port抽象串口的同时，serial core将串口有关的操作函数封装在struct uart\_ops中，底层驱动根据实际硬件情况，填充这些函数，serial core在合适的时候，帮忙调用。

因为在历史上，串口设备是一种非常复杂的设备，因此，和struct uart\_port类似，struct uart\_ops结构也非常庞大，包罗万象，这里简单介绍一些常用的（其它在用到的时候再关注，或者可参考kernel的帮助文档----Documentation/serial/driver）：

> startup，打开串口设备的时候，serial core会调用该接口，driver可以在这里进行串口的初始化操作，例如申请中断资源、使能clock、使能接收，等等；
>
> shutdown，startup的反操作，在串口设备被关闭的时候调用；
>
> start\_tx，每当有一笔新的数据需要通过串口发送出去的时候，serial core会先把数据保存在TX的buffer中（参考3.2.2的介绍），然后调用start\_tx通知driver。driver需要在该接口中，根据当前的状态（TX是否正在进行），决定是否需要发起一次传输；
>
> stop\_tx，停止正在进行中的TX；
>
> stop\_rx，停止RX；
>
> tx\_empty，判断硬件的TX FIFO是否为空，如果是，则返回TIOCSER\_TEMT，否则返回0；
>
> .set\_mctrl，设置modem的control line，可以留空；
>
> .set\_termios，设置串口的termios（例如波特率、数据位、停止位等）。

**3.2.4 struct uart\_driver**

上面介绍的几个数据结构，都在竭力描述串口设备，相应的，按照设备模型的惯例，需要一个和设备对应的、抽象driver数据结构，就是struct uart\_driver：

> struct uart\_driver {   
> struct module \*owner;   
> const char \*driver\_name;   
> const char \*dev\_name;   
> int major;   
> int minor;   
> int nr;   
> struct console \*cons;
>
> /\*   
> \* these are private; the low level driver should not   
> \* touch these; they should be initialised to NULL   
> \*/   
> struct uart\_state \*state;   
> struct tty\_driver \*tty\_driver;   
> };

该数据结构非常简单，一般情况下，只要关注如下的字段：

> driver\_name，driver的名称；
>
> dev\_name，对应的设备名，例如“ttyS”；
>
> nr，该驱动可以支持的串口的数量（serial core会根据这个值为每一个串口分配一些内部使用资源）；
>
> major、minor，主、次设备号，可以不指定（这样的话，TTY core会帮忙动态分配）；
>
> cons，如果需要将某一个串口当作system console，可以在driver中定义struct console变量，并将它的指针保存在这里，serial core会在注册串口的时候帮忙将console注册到系统中。

#### 3.3 向具体driver提供的用于编写串口驱动的API

数据结构抽象完毕后，serial core向下层的driver提供了方便的编程API，主要包括：

1）uart driver有关的API

> int uart\_register\_driver(struct uart\_driver \*uart);   
> void uart\_unregister\_driver(struct uart\_driver \*uart);

uart\_register\_driver，将定义并填充好的uart driver注册到kernel中，一般在驱动模块的init接口中被调用。

uart\_unregister\_driver，注销uart driver，在驱动模块的exit接口中被调用。

2）uart port有关的API

> int uart\_add\_one\_port(struct uart\_driver \*reg, struct uart\_port \*port);   
> int uart\_remove\_one\_port(struct uart\_driver \*reg, struct uart\_port \*port);   
> int uart\_match\_port(struct uart\_port \*port1, struct uart\_port \*port2);   
>   
> int uart\_suspend\_port(struct uart\_driver \*reg, struct uart\_port \*port);   
> int uart\_resume\_port(struct uart\_driver \*reg, struct uart\_port \*port);   
>   
> static inline int uart\_tx\_stopped(struct uart\_port \*port)
>
> extern void uart\_insert\_char(struct uart\_port \*port, unsigned int status,   
> unsigned int overrun, unsigned int ch, unsigned int flag);

uart\_add\_one\_port、uart\_remove\_one\_port，添加/删除一个uart port，一般在platform driver的probe/remove中被调用。

uart\_suspend\_port、uart\_resume\_port，suspend/resume uart port，在电源管理状态切换的时候被调用。

uart\_tx\_stopped，判断某一个uart port的tx是否处于停止状态。

uart\_insert\_char，驱动从串口接收到一个字符之后，可以调用该接口把该字符放到RX buffer中（相比tty\_insert\_flip\_char，可以进行一些overrun的处理）。

3）system console有关的API

> struct tty\_driver \*uart\_console\_device(struct console \*co, int \*index);   
> void uart\_console\_write(struct uart\_port \*port, const char \*s,   
> unsigned int count,   
> void (\*putchar)(struct uart\_port \*, int));

uart\_console\_device，通过console指针获取tty driver指针的帮助函数，通常情况下会把该函数赋值给串口console的.device指针，例如：

> static struct console xxx\_console = {   
> …   
> .device = uart\_console\_device,   
> …   
> };

uart\_console\_write，向串口发送一个字符串的辅助接口，通常在console的.write接口中被调用。

4）其它辅助类的API

> #define uart\_circ\_empty(circ) ((circ)->head == (circ)->tail)   
> #define uart\_circ\_clear(circ) ((circ)->head = (circ)->tail = 0)
>
> #define uart\_circ\_chars\_pending(circ) \   
> (CIRC\_CNT((circ)->head, (circ)->tail, UART\_XMIT\_SIZE))
>
> #define uart\_circ\_chars\_free(circ) \   
> (CIRC\_SPACE((circ)->head, (circ)->tail, UART\_XMIT\_SIZE))

为了方便driver操作环形缓冲区，serial core定义了一些状态判断的宏，例如是否为空（uart\_circ\_empty）、是否为初始状态（uart\_circ\_clear）、缓冲区中有效数据的个数（uart\_circ\_chars\_pending）、缓冲区中空闲空间的个数（uart\_circ\_chars\_free）、等等。

## 4. earlycon

early console是linux serial framework提供的一个可在kernel启动早期使用的console，最早可以在“start\_kernel-->setup\_arch-->parse\_early\_param”之后就可使用，对于kernel早期的debug很有帮助。

根据复杂程度，serial framework提供了两种API，供底层的driver使用。

#### 4.1 静态定义的方式（不需要串口驱动，无法通过device tree动态选择串口）。

这种方法很简单，相关的API包括：

1）EARLYCON\_DECLARE（定义一个early console）

> #define EARLYCON\_DECLARE(\_name, fn) OF\_EARLYCON\_DECLARE(\_name, "", fn)

该函数有两个参数：\_name是early console的名称，需要和后续在命令行参数中指定的一致；fn是一个原型为“int (\*setup)(struct earlycon\_device \*, const char \*options);”的回调函数，用于在kernel启动的时候配置改console。

2）setup

driver需要在setup回调中做两件事情：

> a）初始化early console有关的硬件，例如ioremap、初始化串口控制器、等等。
>
> b）实现一个console->write[2]接口，并将函数指针保存在setup第一个参数的相应指针中（device->con->write）

3）命令行参数（earlycon=xxx）

> 完成上面1）和2）之后，一个earlycon driver就完成了，serial framework会在kernel启动的时候，调用我们提供的setup接口，对early console初始化，然后调用system console core提供的register\_console接口，帮忙注册console[2]。
>
> 如果需要使用这个console，可在kernel启动的时候传入命令行参数“earlycon=xxx”，xxx为early console的名称。

#### 4.2 通过device tree动态选择的方式（和串口驱动配合使用，可以通过dts的stdout-path或者linux,stdout-path指定使用哪个串口）。

这种方法稍显麻烦，有违earlycon的初衷，暂不介绍了，感兴趣的同学可以自行研读代码。

## 5. 基于serial framework编写串口驱动的方法

可参考如下文章：

> [X-012-KERNEL-serial early console的移植](/x_project/kernel_earlycon_porting.html)
>
> [X-016-KERNEL-串口驱动开发之驱动框架](/x_project/serial_driver_porting_1.html)
>
> [X-017-KERNEL-串口驱动开发之uart driver框架](/x_project/serial_driver_porting_2.html)
>
> [X-018-KERNEL-串口驱动开发之serial console](/x_project/serial_driver_porting_3.html)
>
> [X-019-KERNEL-串口驱动开发之数据收发](/x_project/serial_driver_porting_4.html)

## 6. 参考文档

[1] TTY子系统，[/sort/tty_framework](/sort/tty_framework "/sort/tty_framework")

[2] [Linux TTY framework(5)\_System console driver](/tty_framework/system_console_driver.html)

*原创文章，转发请注明出处。蜗窝科技*，[www.wowotech.net](/comm/serial_overview.html)。

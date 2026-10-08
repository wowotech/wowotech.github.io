---
title: "X-019-KERNEL-串口驱动开发之数据收发"
date: 2016-11-29T21:55:06+08:00
url: "/x_project/serial_driver_porting_4.html"
gid: "359"
emlog_type: "blog"
summary: "\r\n\t本文是“X \r\nProject”串口驱动开发的第四篇，在第二篇“uart \r\ndriver框架[1]”的基础上，实现基本的、可收发数据的uart驱动，并借助这个过程，学习如下知识：\r\n\r\n\r\n\t\r\n\t\t中断的申请和使用；\r\n\t\r\n\t\r\n\t\t利用中断发送和接收数据；\r\n\t\r\n\t\r\n\t\tuart_ops中常用函数（.startup, .start_tx, etc.）的使用。\r\n\t\r\n"
author: "wowo"
category: "X Project"
category_alias: "x_project"
tags: ["Linux", "driver", "irq", "serial", "tx", "rx", "transmit"]
views: 13305
comment_count: 7
aliases:
  - "/x_project/359.html"
  - "/359.html"
---

## 1. 前言

本文是“[X Project](/sort/x_project)”串口驱动开发的第四篇，在第二篇“[uart driver框架](/x_project/serial_driver_porting_2.html)”的基础上，实现基本的、可收发数据的uart驱动，并借助这个过程，学习如下知识：

> 中断的申请和使用；
>
> 利用中断发送和接收数据；
>
> uart\_ops中常用函数（.startup, .start\_tx, etc.）的使用。

## 2. 中断的申请和使用

在linux kernel中，使用中断进行数据传输是最基本的要求（更进阶的是DMA，我们会在后续的文章中介绍），因为强悍的CPU无法忍受乌龟般的外设速度，忙等待只会自断生路。下面将会以Bubblegum-96平台的UART driver为例，介绍中断的使用。

#### 2.1 准备工作

关于中断，在使用之前，我们至少需要先理清如下内容（以Bubblegum-96平台的UART5为例进行说明）：

1）该外设和中断控制器之间通过哪些中断线（IRQ line，也就是我们常说的中断号）进行连接。

2）每个中断线的触发方式为何，电平？边沿？

> 由[2]可知，Bubblegum-96平台的UART5的中断线为SPI 35，触发方式为高电平触发（外部GPIO中断比较关心触发方式，其它的外设中断，一般都是电平触发）。

3）在设备内部（例如这里的UART控制器），哪些行为可以产生中断？产生中断的条件为何？如何控制中断的使能？如何清除中断的pending状态？

> 对Bubblegum-96平台的UART5控制器来说，由[1]可知：
>
> 有TX和RX两种中断；
>
> TX的FIFO大小为32bytes，只要空闲空间（empty）大于等于16bytes，就会触发中断；
>
> RX的FIFO大小也为32bytes，当接收的数据大于等于16bytes时，就会触发中断；
>
> TX/RX中断使能与否，可由UARTx\_CTL（offset=0x0000）的bit19、bit18控制；
>
> UART5中断产生时，可通过UARTx\_STAT（offset=0x000c）的bit1（TX IRQ Pending）、bit0（RX IRQ Pending）获取具体的中断原因（TX还是RX），这两个bit均写1清除。

注1，这里存在一个问题，需要大家思考（这个问题是串口驱动最常见的）：基于上面的描述，只有RX接收到大于等于16bytes的数据时，才会产生中断，那么接收少于16bytes的数据时，怎么办？后面实际调试的时候，再细说。

4）中断发生时，要做哪些事情？这些事情是否比较耗时？是否可以在线程中处理？

> 以UART控制器为例：
>
> TX中断产生时，表明可以向TX FIFO写入数据；
>
> RX中断产生时，表明RX FIFO中有数据需要读取；
>
> 在Linux serial framework下，上面两个动作都不是耗时的动作，因此不需要在线程中进行处理。

#### 2.2 中断申请

对uart driver来说，中断的申请，包括3个步骤：

1）在DTS中，通过interrupts字段，指定该设备需要使用的中断号

> serial5: serial@e012a000 {   
> compatible = "actions,s900-serial";   
> reg = <0 0="" 0xe012a000="" 0x2000="">; /\* UART5\_BASE \*/   
> + interrupts = ;  
> };

2）在platform driver的probe接口中，通过platform\_get\_irq接口，将DTS中指定的中断号取出并保存下来

> @@ -253,6 +268,12 @@ static int owl\_serial\_probe(struct platform\_device \*pdev)   
> }   
> port->iotype = UPIO\_MEM32;
>
> + port->irq = platform\_get\_irq(pdev, 0);  
> + if (port->irq < 0) {   
> + dev\_err(&pdev->dev, "Failed to get irq\n");   
> + return port->irq;   
> + }   
> +   
> port->line = of\_alias\_get\_id(pdev->dev.of\_node, "serial");

platform\_get\_irq第二个参数是dts中interrupts字段指定的中断编号，我们只使用一个，因此这里为0即可。

3）在uart port的.startup接口中，调用devm\_request\_irq，申请并使能该中断线

注2：这里的使能，是指UART控制器和GIC之间的使能。

> +static irqreturn\_t owl\_serial\_irq\_handle(int irq, void \*data)   
> +{   
> + struct uart\_port \*port = data;  
> +   
> + return IRQ\_HANDLED;   
> +}   
> +   
> static int owl\_serial\_startup(struct uart\_port \*port)   
> {   
> int ret = 0;
>
> dev\_dbg(port->dev, "%s\n", \_\_func\_\_);
>
> + ret = devm\_request\_irq(port->dev, port->irq, owl\_serial\_irq\_handle,   
> + 0, "owl\_serial", port);  
> + if (ret < 0) {   
> + dev\_err(port->dev, "request irq(%d) failed(%d)\n",   
> + port->irq, ret);   
> + return ret;   
> + }   
> +   
> return ret;   
> }

devm\_request\_irq有很多参数，其中“owl\_serial\_irq\_handle”是中断的handler，0是flags（这里没有特殊的flag需要传递），"owl\_serial"是名字（无关紧要），port是传入的私有数据，kernel irq core会在调用我们的handler的时候再传给我们（具体请参考上面owl\_serial\_irq\_handle函数）。

#### 2.3 RX和TX中断的使能

串口在启动（.startup被调用）之后，就要保证可以正常接收数据，因此RX中断需要在uart port的.startup中使能：

> @@ -111,6 +120,9 @@ static int owl\_serial\_startup(struct uart\_port \*port)   
> return ret;   
> }
>
> + /\* RX irq enable \*/   
> + \_\_PORT\_SET\_BIT(port, UART\_CTL, UART\_CTL\_RXIE);  
> +   
> return ret;   
> }

而TX中断可以放到uart port的.start\_tx中再使能，如下：

> static void owl\_serial\_start\_tx(struct uart\_port \*port)   
> {   
> dev\_dbg(port->dev, "%s\n", \_\_func\_\_);   
> +   
> + /\* TX irq enable \*/   
> + \_\_PORT\_SET\_BIT(port, UART\_CTL, UART\_CTL\_TXIE);  
> }

#### 2.4 中断处理

中断处理的逻辑比较简单：

> 1）读取UARTx\_STAT寄存器，判断中断类型。
>
> 2）如果是RX中断，从UARTx\_RXDAT中读取数据，并调用tty\_insert\_flip\_char将读取的数据保存在uart port的RX buffer中。具体可参考第4章的介绍。
>
> 3）如果是TX中断，则检查uart port的TX buffer，是否还有未发送的数据，如果有，则将数据写入到UARTx\_TXDAT，由UART控制器发送出去。具体可参考第3章的介绍。

## 3. 收据收发前的其它操作

在前面的章节提到过，uart driver需要实现由struct uart\_ops变量所代表的各种回调函数，这里列举一些和数据收发直接相关的函数，如下：

1）.startup，除去上面2.3中申请终端、使能RX中断等操作，我们还需要在startup的时候，使能串口控制器，如下：

> @@ -123,6 +123,9 @@ static int owl\_serial\_startup(struct uart\_port \*port)   
> /\* RX irq enable \*/   
> \_\_PORT\_SET\_BIT(port, UART\_CTL, UART\_CTL\_RXIE);
>
> + /\* enable serial port \*/   
> + \_\_PORT\_SET\_BIT(port, UART\_CTL, UART\_CTL\_EN);   
> +   
> return ret;   
> }

2）.shutdown，.startup的反动作，disable串口控制器、disable RX中断、注销中断等，不再贴代码了。

3）.stop\_tx，disable TX中断，以及其它和数据发送有关的内容（具体可参考第4章的描述）。

4）.stop\_rx，disable RX中断，以及其它和数据接收有关的内容（具体可参考第5章的描述）。

5）.tx\_empty，判断TX FIFO是否为空，如下（如果为空，需要返回TIOCSER\_TEMT，否则返回0即可）：

> @@ -153,7 +167,10 @@ static unsigned int owl\_serial\_tx\_empty(struct uart\_port \*port)   
> {   
> dev\_dbg(port->dev, "%s\n", \_\_func\_\_);
>
> - return 0;   
> + if (\_\_PORT\_TEST\_BIT(port, UART\_STAT, UART\_STAT\_TFES))   
> + return TIOCSER\_TEMT;   
> + else   
> + return 0;  
> }

## 3. 数据发送

上层软件需要通过uart port发送的数据时，会将数据暂存在一个struct circ\_buf类型的环形缓冲区中（port->state->xmit），然后调用driver的.start\_tx接口，我们可以在这个接口中从环形缓冲区读取数据要发送的数据，写入到UART控制器的TX FIFO。当然，TX FIFO可能很小，需要多次传输才能完成，因此我们需要在传输完成的中断中，再次从环形缓冲区读取数据，写入TX FIFO，直到所有数据发送完成为止。上述的发送流程图如下：

[![serial_tx_flow](/content/uploadfile/201611/3700287652bedd57edc00aa0b04cfd2b20161129135503.gif "serial_tx_flow")](/content/uploadfile/201611/e3d6f97b2d040997cc0fc9f13b9e691e20161129135503.gif)

图片1 数据发送流程

该流程比较简单（具体的代码实现可参考本文档对应的patch文件），不过有一些地方需要说明一下：

> 1）.start\_tx实在关中断的情况下调用的，因此不用考虑同步问题。
>
> 2）由于TX FIFO的限制，大多数情况下，数据发送是由TX中断推动的。但存在一种特殊情况：TX buffer的数据已经发送完成了，此时串口控制器没有数据在发送，TX中断不会产生，此时需要在.start\_tx中重新写FIFO。上面图片1的流程，可以覆盖这个场景。

## 4. 数据接收

数据接收的流程更简单，流程图如下：

[![serial_rx_flow](/content/uploadfile/201611/c534a0cd3868aad8225a4893c60e056820161129135505.gif "serial_rx_flow")](/content/uploadfile/201611/e45fd1cb687e215b4320cf2f0d2d421f20161129135504.gif)

图片2 数据接收流程

## 5. 串口数据发送和console之间的同步

由于console的write，和串口数据的发送，都是操作同一个TX FIFO，因此存在数据交叉的问题。要解决这个问题，一般遵守一个原则：保证一次console write的完整性，这样可以避免kernel输出日志被打乱。为了做到这一点，我们需要按照如下步骤改造console的write接口：

1）备份当前TX中断的状态，然后禁止TX中断。

2）按照原来的方式，调用uart\_console\_write将字符串通过串口发送出去。

3）恢复TX的中断状态。

代码如下：

> static void owl\_console\_write(struct console \*con, const char \*s, unsigned n)   
> {   
> + bool tx\_irq\_enabled;   
> +   
> struct uart\_driver \*driver = con->data;   
> struct uart\_port \*port = driver->state[con->index].uart\_port;
>
> + /\* save TX IRQ status \*/   
> + tx\_irq\_enabled = \_\_PORT\_TEST\_BIT(port, UART\_CTL, UART\_CTL\_TXIE);   
> +   
> + /\* TX irq disable \*/   
> + \_\_PORT\_CLEAR\_BIT(port, UART\_CTL, UART\_CTL\_TXIE);   
> +   
> uart\_console\_write(port, s, n, owl\_console\_putchar);   
> +   
> + /\* restore TX IRQ status \*/   
> + if (tx\_irq\_enabled)   
> + \_\_PORT\_SET\_BIT(port, UART\_CTL, UART\_CTL\_TXIE);   
> }

## 6. 参考文档

[1] [bubblegum-96/SoC\_bubblegum96.pdf](https://github.com/96boards/documentation/blob/master/ConsumerEdition/Bubblegum-96/AdditionalDocs/SoC_bubblegum96.pdf)

[2] <https://github.com/96boards-bubblegum/linux/blob/bubblegum96-3.10/arch/arm64/boot/dts/s900.dtsi>

[3] Documentation/serial/driver

[4] patch文件，[https://github.com/wowotechX/linux/commit/9328d8aa82dcf2c17eec03c1beccf9c5c0567a6a](https://github.com/wowotechX/linux/commit/9328d8aa82dcf2c17eec03c1beccf9c5c0567a6a "https://github.com/wowotechX/linux/commit/9328d8aa82dcf2c17eec03c1beccf9c5c0567a6a")

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/x_project/serial_driver_porting_4.html)。

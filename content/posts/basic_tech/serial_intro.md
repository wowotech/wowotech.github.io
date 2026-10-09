---
title: "串口通信技术浅析"
date: 2016-06-24T22:50:11+08:00
url: "/basic_tech/serial_intro.html"
gid: "315"
emlog_type: "blog"
summary: "最熟悉的陌生人！用这句话形容“串口”是再贴切不过的了。 对嵌入式工程师来说，“串口”是一个再熟悉不过的模块，熟悉到像喝水一样自然。与此同时，有关串口的很多细节，却被渐渐地模糊和忽略，例如： 我们经常挂在嘴边的serial、UART、RS232等概念，究竟是怎么回事？它们之间有何联系？有何区别？ 串口的波特率（baud rate）是怎么定义和计算的？比特率（bit rate）又是怎么回事？二者的关系"
author: "wowo"
category: "基础技术"
category_alias: "basic_tech"
tags: ["uart", "serial", "baud", "rate"]
views: 19815
comment_count: 1
aliases:
  - "/basic_tech/315.html"
  - "/315.html"
---

#### 1. 前言

最熟悉的陌生人！用这句话形容“串口”是再贴切不过的了。

对嵌入式工程师来说，“串口”是一个再熟悉不过的模块，熟悉到像喝水一样自然。与此同时，有关串口的很多细节，却被渐渐地模糊和忽略，例如：

> 我们经常挂在嘴边的serial、UART、RS232等概念，究竟是怎么回事？它们之间有何联系？有何区别？
>
> 串口的波特率（baud rate）是怎么定义和计算的？比特率（bit rate）又是怎么回事？二者的关系又是怎样？
>
> 为什么波特率有误差？通信过程中所容许的误差范围是多少？

本文将对上述问题，进行简单的总结和归纳，以便指导有关的开发工作。

#### 2. 概念解释

##### 2.1 串行通信（Serial communication）

在通信和计算机科学中，Serial communication是一个通用概念，泛指所有的串行的通信协议，如RS232、USB、I2C、SPI、1-Wire、Ethernet等。这里的串行（serial），是相对并行通信（parallel communication）来说的，如下图：

[![Parallel_and_Serial_Transmission](/content/uploadfile/201606/2a0acc95357f72116b5c83191c6ee41320160624145003.gif "Parallel_and_Serial_Transmission")](/content/uploadfile/201606/3daabdd8ac61edf21d0d1d29c33f128a20160624144953.gif)

图片1 并行通信和串行通信

上面图片1是非常容易理解的，这里不再过多解释，有关串行通信的优缺点，可参考“Serial communication[1]”中的解释。

##### 2.2 同步串行通信（Synchronous serial communication）和异步串行通信（Asynchronous serial communication）

理解串行通信的概念之后，大家可能会有疑问：接收方接收到一长串的、表示0/1电平跳变的信号之后，怎么还原出有效的信息呢？有两种方法：

> 1）发送端在发送串行数据的同时，提供一个时钟信号，并按照一定的约定（例如在时钟信号的上升沿的时候，将数据发送出去）发送数据，接收端根据发送端提供的时钟信号，以及大家的约定，接收数据。这就是常说的同步串行通信（Synchronous serial communication），I2C、SPI等有时钟信号的协议，都属于这种通信方式。
>
> 2）发送端在数据发送之前和之后，通过特定形式的信号（例如START信号和STOP信号），告诉接收端，可以开始（或者停止）接收数据了。与此同时，收发两方会约定一个数据发送的速度（就是大名鼎鼎的波特率），发送端在发送START信号之后，就按照固定的节奏发送串行数据，与此同时，接收端在收到START信号之后，也按照固定的节奏接收串行数据。这就是常说的异步串行通信（Asynchronous serial communication），我们本节的主角----串口通信，就是这种通信方式。

注1：严格意义上，START/STOP形式的异步串行通信，称作“asynchronous start-stop communication”，但由于这种形式在异步串行通信里面使用太广泛了，二者也就混为一谈、不加区分了。

注2：根据同步方式的不同，串口也包括异步串口和同步串口两种。本文所指的串口，都是只异步串口。

##### 2.3 串口（Serial port）和RS-232

在计算机的世界里，“串口”是使用串行的方式进行数据传输的一种接口，它是相对于计算机的并行接口来说的。虽然串行通信可以通过多种技术实现（如USB、Ethernet等），但由于历史原因，我们所说的串口，特指符合RS-232规范的接口，下图就是我们比较常见的一种：

[![Serial_port](/content/uploadfile/201606/c1970106f8c5b2e4abfbe0cc90941e2c20160624145009.gif "Serial_port")](/content/uploadfile/201606/7c59036701c06f0975fb73217ff4bb1220160624145008.gif)

图片2 male DE-9 connector

串口是用于实现串行通信的物理接口的一种统称，但只有名称还远远不够，通信的双方需要一些约定和规范，才能正确的进行数据传输，例如需要哪些信号线、信号的电平如何、接口的形状如何、数据的编码格式、数据传输的速率、等等。

在串口通信中，这些内容主要由两部分定义：

1）RS-232（有时候也称作RS-232-C，C是版本）规范，定义“硬件相关”的特性，包括：

> 电气信号特性，如信号电平（-3V～-15V表示逻辑1，+3～+15V表示逻辑0）等；
>
> 接口特性，如连接器（connectors）的定义（9-pin的 DE-9 Male/Female，25-pin的DB-25 Male/Female等）、管脚信号的定义、等等；
>
> 电缆（cable）的特性，如电缆的长度（RS-232没有显式的限制电缆的长度，但限制了电容，效果一样）等；
>
> 等等。

2）串口硬件，定义“软件相关”的特性，包括：

> 数据的编码格式（character encoding），就是上面提到的“asynchronous start-stop”格式，也即我们所熟知的的“起始位、数据位、校验位、停止位“；
>
> 数据传输的bit rates，也即我们熟悉的波特率（baud rate）。

注3：说来奇怪，RS-232规范规定了串口通信有关的方方面面的特性，唯独没有规定数据传输相关的编码格式和bit rates。可能是硬件的差异太大，以至于该规范无法完全覆盖。

注4：虽然RS-232规范没有规定bit rates，但它做了一个要求----不能超过20Kbps，虽然从现在来看，这就是瞎扯，呵呵。

注5：RS-232定义了各种形态的串口接口，如DE-9、DB-25等等，但这大多和上古时代的通信有关场景以有关，随着数字通信的普及，以及USB等协议的蚕食，这些庞然大物已经越来越少见了。反而在嵌入式场景中，一些简化的形态，如4线（VCC/RX/TX/GND）串口等，反而使用的比较多。

##### 2.4 UART(Universal Asynchronous Receiver/Transmitter)

我们在上一节（2.3）提到，由于硬件的差异太大，RS-232并没有规定串口通信的编码格式和bit rates。因此，这一块的实现，完全由具体的硬件（或者对应的软件负责）。

在早期的产品中，大多使用软件的方式，以一定的速率（bit rates），产生出符合编码格式的bit流。但后来为了提升性能，很多产品（如IBM的PC）使用了专门的硬件模块，完成这个事情，这就是我们经常挂在嘴边的UART。

至此，串口通信有关的术语已经悉数登场，简单总结一下吧：

> 串行通信（serial communication），泛指使用bit流的形式进行数据通信的方法。
>
> 同步串行通信（Synchronous serial communication）和异步串行通信（Asynchronous serial communication），串行通信的不同实现方法，主要区别在于同步的方式。
>
> 串口（serial port），特指使用“异步串行通信”的方法进行数据通信的接口，主要是从硬件的角度描述的。
>
> RS-232，定义两个串口之间通信行为的一个规范，偏向于电平、连接器、电缆等硬件特性。
>
> UART（Universal Asynchronous Receiver/Transmitter），一个硬件模块，根据串口硬件所规定编码格式、bit rate，产生处通信所需的bit流。

##### 2.5 TTL电平转换以及USB转串口

最后，再念叨一下TTL电平转换有关的概念。当前，串口应用最广泛的场景，就是嵌入式产品和PC之间的一些数据交互，如debug输出、firmware更新等。但这里有一个比较麻烦的事情：

> PC串口符合RS-232规范，其电平是“-3V～-15V/+3～+15V”。而大多数的嵌入式产品，都是使用TTL电平（如0v/3.3v）。因此，这两种电平无法直接连接。怎么办呢？增加一个电平转换电路就是了，于是嵌入式产品和PC之间的连接就变成了如下的形式：   
> PC(串口)<---------->电平转换电路<---------->嵌入式产品(串口)

还有更麻烦的事情，随着技术的进步，串口这样的大杀器，渐渐地被PC抛弃了，怎么办呢？USB转串口应运而生了，连接方式变成了：

> PC(USB接口)<---------->USB转串口<---------->嵌入式产品(串口)

#### 3. 波特率（baud rate）和比特率（bit rate）

理解了串口中这些既熟悉又陌生的术语之后，我们再来看看波特率（baud rate）。

说实话，在数据通信中，比特率（bit rate）比较容易理解，就是一定时间内，能够传输多少个bit。例如bps，就是bit per second的缩写。那什么事波特率呢？

在通信中，波特率也称作符号速率（symbol rate），指的的是“数据变化”的速率。说着很拗口，我们举个例子：

> 在计算机系里，小杨和小李是一对好基友，不过小杨是学霸、小李是学渣。所以，期末考试到了，小杨决定“鼎力相助”。怎么办呢？
>
> 二人约定，考试时，小杨携带黑色和白色两支笔，根据两支笔出现的情况，表示A、B、C、D四种答案，即：   
> 白色的笔没有出现 黑色的笔没有出现 A   
> 白色的笔没有出现 黑色的笔出现 B   
> 白色的笔出现 黑色的笔没有出现 C   
> 白色的笔出现 黑色的笔出现 D
>
> 同时约定，在考试开始1小时之后，小杨从第1道选择题开始，以每分钟更换一次的速度，更换答案。小李按照这个速度，以及大家的约定，通过观察两支笔出现的情况，获得答案。

确实是个好方法，不过仔细想想，这其实是一个典型的异步通信过程。通信的过程中，答案更新的速度（每分钟1次），就是我们所说的baud rate（或者symbol rate），即1 bd per minute（可以把bd看着baud的单位）。

与此同时，每次更新，传递了多少信息呢？表面上看是A、B、C、D，本质上是由白和黑所代表的两个bit，00、01、10或者11。因此，每次更新传递2个bit的信息，所以bit rate就是2 bits per minute。

上面的例子中，通信的波特率和比特率是不同的，分别为1和2（per minute），而有些通信系统，例如我们所熟知的串口通信，它们却是一样的，例如我们说115200的波特率，实际上的比特率也是115200。因为一次只传输1个bit（0或者1）。

#### 4. 帧格式和波特率误差

我们知道，串口通信的数据格式包括start bit、data bits、parity bit和stop bits，其中：

> start bit固定为1bit；
>
> data bits可以为5、6、7、8或者9bits，不过常用的都是8bits；
>
> parity bit是非必须的，一般为0bit；
>
> stop bit可以是1bit和2bits两种，一般都是1bit。

图示如下：

[![Puerto_serie_Rs232](/content/uploadfile/201606/381c22fef1f91128d78a2bd1abe3234d20160624145010.gif "Puerto_serie_Rs232")](/content/uploadfile/201606/b5e9eb9e2e22ce9d9a3e24918a804f8120160624145010.gif)

图片2 串口帧格式

因此，从本质上讲，波特率定义了帧格式中每一个bit的信号的持续时间，即1 / bard rate。而一帧数据传输完成，需要的时间为(1 / bard rate) \* 10（以8N1的帧格式为例）。

这种异步通信的方法，有一个坏消息，也有一个好消息：

> 坏消息是，受系统时钟精度、分频系数等影响，波特率可能不精确，存在误差。而在一帧数据的传输过程中，误差会累积。
>
> 好消息是，如果误差累积的不多，受start/stop信号的矫正作用，下一帧数据中，可将累积误差清零。
>
> 关于误差，我们再稍微详细分析一下。

根据我们的常识，信号是在中间点采样，因此，在一帧数据中，如果误差累积超过(1 / bard rate / 2)的时间，则数据会采样错误。假设理想的baud rate是BDi，实际的baud rate是BDr，则：

> 每一个bit的误差时间是：1 / BDi – 1 / BDr。
>
> 10个bit的误差时间是：10 \* (1 / BDi – 1 / BDr)。
>
> 因此，安全的误差范围是：abs(10 \* (1 / BDi – 1 / BDr)) < 1 / BDi / 2。

以115200的波特率为例，带入上面的公式：

> abs(10 \* (1 / 115200– 1 / BDr)) < 1 / 115200 / 2
>
> -1 / 115200 / 2 < 10 \* (1 / 115200– 1 / BDr) < 1 / 115200 / 2
>
> (20 / 21) \* 115200 < BDr < (20 / 19) \* 115200

因此，115200波特率所容许的误差范围是20 / 21 ~ 20 / 19，即+/- 5%。其它波特率也可以带入公式去计算。另外，如果双方都有误差的话怎么办？嘿嘿，你懂的，除2吧。

#### 5. 参考文档

[1] Serial communication，[https://en.wikipedia.org/wiki/Serial\_communication](https://en.wikipedia.org/wiki/Serial_communication "https://en.wikipedia.org/wiki/Serial_communication")

[2] Serial port，[https://en.wikipedia.org/wiki/Serial\_port](https://en.wikipedia.org/wiki/Serial_port "https://en.wikipedia.org/wiki/Serial_port")

[3] RS-232，[https://en.wikipedia.org/wiki/RS-232](https://en.wikipedia.org/wiki/RS-232 "https://en.wikipedia.org/wiki/RS-232")

[4] Asynchronous serial communication，[https://en.wikipedia.org/wiki/Asynchronous\_serial\_communication](https://en.wikipedia.org/wiki/Asynchronous_serial_communication "https://en.wikipedia.org/wiki/Asynchronous_serial_communication")

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/basic_tech/serial_intro.html)。

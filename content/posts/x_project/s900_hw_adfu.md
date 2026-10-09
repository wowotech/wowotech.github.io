---
title: "X-002-HW-S900芯片boot from USB有关的硬件描述"
date: 2016-05-12T22:01:18+08:00
url: "/x_project/s900_hw_adfu.html"
gid: "294"
emlog_type: "blog"
summary: "本文将以S900芯片 [1] 为例，介绍和“ 【任务1】启动过程-Boot from USB ” 有关的硬件行为。其它人可以借鉴该文档，描述自己所使用平台的硬件特性，以完成该任务。 为了方便操作，这里以“填空题”的形式，给出我们关心的key point，只要我们能够把这些填空题完成，就可以放心的去coding了。题目如下： 1）CPU上电后，从 哪种设备（ ）的 哪个地址（ ） 开始执行。 2）用"
author: "wowo"
category: "X Project"
category_alias: "x_project"
tags: ["USB", "s900", "hw", "boot"]
views: 17236
comment_count: 18
aliases:
  - "/x_project/294.html"
  - "/294.html"
---

#### 1. 前言

本文将以S900芯片[1]为例，介绍和“[【任务1】启动过程-Boot from USB](/forum/15.html)**”**有关的硬件行为。其它人可以借鉴该文档，描述自己所使用平台的硬件特性，以完成该任务。

为了方便操作，这里以“填空题”的形式，给出我们关心的key point，只要我们能够把这些填空题完成，就可以放心的去coding了。题目如下：

> 1）CPU上电后，从哪种设备（ ）的哪个地址（ ）开始执行。
>
> 2）用（ ）方式，可以让CPU进入USB download（或者UART download）模式。
>
> 3）进入USB download之后，设备使用哪个USB接口（ ）和主机通信。
>
> 4）进入download模式后，哪一段地址范围（通常为SRAM）可以用来执行程序：（ ）~（ ），size有多大（ ）。
>
> 5）用什么协议（ ）可以通过USB将bin文件上传到指定的地址。
>
> 6）用什么协议（ ）可以让CPU跳转到到指定地址继续执行。

注1：Boot这一块的资料，国内的IC设计厂商给出的资料都是语焉不详，从哪里得到有用的信息，是一个相当困难的事情。大家只能各显神通了。

#### 2. 答题过程

##### 2.1 Boot from ROM

由“S900 IC Spec1.6小节 System Boot[1]”的描述可知，S900在上电后，会从BROM的初始地址执行boot code（此code可称为Initial Boot Loader，IPL）。同时，由“1.7小节Address Mapping[1]“的描述可知，BROM的地址范围为[0xFFFF0000, 0xFFFFFFFF]。因此，题目1的答案就出来了：

> CPU上电后，从（Boot ROM）的（0xFFFF0000）开始执行。

注2：Boot ROM的执行地址，和本文的任务没有直接关系，因此大家不用太在意。

##### 2.2 进入USB download（DFU）模式

同样，由“SoC\_bubblegum96.pdf 1.6小节 System Boot[1]”的描述可知，Boot ROM的代码开始执行之后，会依次从NAND Flash、SPI NOR 和SD/MMC/eMMC等存储介质中查找有效的boot code（此code可称为Second Boot Loader，SPL，这个过程会在后面Boot from eMMC等任务中介绍），如果没有找到，则将名称为ADFULauncher的代码从Boot ROM中加载到SRAM并执行。ADFULauncher负责通过USB接口和主机通信，以便将主机上的bin文件加载到板子上并运行，这就是传说的“Boot from USB”。

因此，进入USB download（后面简称DFU，Device Firmware Upgrade）的方法，就是各种存储介质中，都没有有效的boot code。对S900 96board来说，可用于boot的存储介质是SD卡和eMMC[2]，因此，只要不插SD卡，同时eMMC中不存在有效数据即可。不插SD卡好办，eMMC中没有有效数据是什么意思呢？

其实Boot ROM从存储介质中读取boot code的时候，会进行一些校验（如固定的标识、checksum等），如果校验失败，则认为boot code无效。因此，对S900 96board就采用了比较粗暴的方法进入DFU模式：将eMMC控制器的data0接地（就无法读到有效数据了），如下（具体可参考S900 96board原理图[3]）：

[![s900_96board_adfu_key](/content/uploadfile/201605/a380afa4ae5ed68297c125e9dca8c74520160512140116.gif "s900_96board_adfu_key")](/content/uploadfile/201605/599c9d99268f2653d456d2cd9a3861a720160512140116.gif)

图片1 s900\_96board\_adfu\_key

上图SW3按下的时候，data0会对地短路，因此，在S900 96board上电的过程中，按住SW3，就可以进入DFU模式（图中称作ADFU，是Action DFU的简称）。所以，题目2的答案也出来了：

> （上电的过程中，按住SW3按键），可以让CPU进入USB download（或者UART download）模式。

注3：ADFULauncher是一段固化在Boot ROM的代码，会在ADFU的时候被拷贝到SRAM中执行，负责通过USB接口和主机通信，以加载firmware。

注4：有关SW3按键在开发板上的位置，可以参考“S900 96board硬件手册[2]”的“2 PCB TOP & BOT Side”章节的说明。

##### 2.3 使用哪个USB接口和主机通信

由“S900 96board硬件手册[2]”的“4.8.1 USB-Host ports”章节的说明可知，S900使用TypeA接口的JUSB1（USB3.0）进行ADFU操作。因此，题目3的答案是：

> 进入USB download之后，设备使用（JUSB1接口）和主机通信。

注5：有关JUSB1在开发板上的位置，可以参考“S900 96board硬件手册[2]”的“2 PCB TOP & BOT Side”章节的说明。

注6：USB TypeA接口和我们电脑上常用的哪种插U盘的接口一样，因此需要特殊的USB连接线（两端都和U盘的连接头一样）才能连接S900 96board开发板和电脑，这种线材不是很常用，只能说这是个SB设计了！！

#### 2.4 SRAM地址范围

“S900 IC Spec[1]”在“1.7 Address Mapping”章节有关SRAM地址范围的描述如下：

> |  |  |  |  |
> | --- | --- | --- | --- |
> | 0xE4060000 | 0xE40BFFFF | 384K | ShareSRAM    1. 0xE4060000~0xE4067FFF    (Independent 32KB SRAM for secure world)    2. 0xE4068000~0xE407FFFF    (96KB SRAM shared from DE) |

由此可知，S900 IC具有384K的SRAM，其中前面32K（0xE4060000~0xE4067FFF）保留给secure world使用，0xE4068000~0xE407FFFF之间的96K，和DE（Display Engine）共用。按理说boot阶段不需要显示的话，和DE共用的SRAM应该可以使用，因此，可供使用的SRAM范围就是0xE4068000~0xE40BFFFF的352K？

好吧，我承认我失败了，实际情况不是这样的，请看下面一张图片（这些信息在公共渠道是拿不到，我们也是多方打听，费尽心思才收集到，如果大家手上的板子也有类似情况，这个任务就麻烦了……）：

[![s900_ADFULancher](/content/uploadfile/201605/97b5cba77a4090aba86bc41670a448f220160512140118.gif "s900_ADFULancher")](/content/uploadfile/201605/445f33116d2250fb0e213ce0e02e52c420160512140117.gif)

图片2 S900 ADFULauncher执行情况

由上面图片可知，Boot ROM代码会在进行ADFU的时候，将12.5KB大小的ADFULancher拷贝到SRAM的0xe4068000~0xe406b1ff处执行（为什么不直接在Boot ROM执行？？？？），并使用0xe407efff为堆栈的基址（向上递增）。另外，0xe407f000~0xe407ffff处不知道被什么东西占用了。所以能够使用的SRAM空间是（问题4的答案？）：

> 0xe406b200往下的，不能超过80K（不太确定）的范围？
>
> 另外，0xe4080000到0xE40BFFFF共256K的地址范围呢？能不能用？鬼知道，后面写代码试一下好了。

##### 2.5 通过ADFU将主机上的bin文件上传到SRAM的指定地址并执行

问题5和问题6属于DFU USB download protocol的范围，按理说，一个正常的芯片，需要把这个协议开放出来给大家使用，这样才能编写boot有关的代码，但遗憾的是，我们没有拿到S900这方面的资料。只能说国内的IC设计厂商是相当的奇葩啊。

不过总有办法，经过绞尽脑汁的搜索，我发现了Linaro写的一份ADFU的代码[4]，通过猜测加想象，我在代码中找到了我想要的东西，总结如下：

1）USB download protocol使用地址为0x1的端点（Out类型的Endpoint）上传数据（主机到开发板方向），使用地址为0x82的端点（IN类型的Endpoint）返回结果（开发板到主机方向）。

2）USB的传输类型为bulk。

3）数据交互的过程，利用了USB Mass Storage协议，具体过程后续会结合USB Mass Storage协议以及Linaro的代码[4]再详细说明。因此，问题5和问题6的答案，暂时不在这里总结了。

注7：有关USB的知识，会在后续的文章中介绍，或许蜗窝USB子系统的分析文章，也可以顺势展开了。

#### 3. 总结

受限于IC厂商的莫名其妙，提供的boot有关的资料少之又少，本文完成的并不理想，但总算勉强可以继续“[【任务1】启动过程-Boot from USB](/forum/15.html)**”。**希望大家在自己的板子上，能够得到尽量多的信息和资源。同时在这里呼吁，国内的IC设计商，应能尽量的包容和开发，只有这样才能越来越强大。

#### 4. 参考文档

[1] S900 IC Spec，[https://github.com/96boards/documentation/blob/master/bubblegum-96/SoC\_bubblegum96.pdf](https://github.com/96boards/documentation/blob/master/bubblegum-96/SoC_bubblegum96.pdf "https://github.com/96boards/documentation/blob/master/bubblegum-96/SoC_bubblegum96.pdf")

[2] S900 96board硬件手册，[https://github.com/96boards/documentation/blob/master/bubblegum-96/HardwareManual\_Bubblegum96.pdf](https://github.com/96boards/documentation/blob/master/bubblegum-96/HardwareManual_Bubblegum96.pdf "https://github.com/96boards/documentation/blob/master/bubblegum-96/HardwareManual_Bubblegum96.pdf")

[3] S900 96board原理图，[https://github.com/96boards/documentation/blob/master/bubblegum-96/bubblegum-96\_Schematic\_V1.0.pdf](https://github.com/96boards/documentation/blob/master/bubblegum-96/bubblegum-96_Schematic_V1.0.pdf "https://github.com/96boards/documentation/blob/master/bubblegum-96/bubblegum-96_Schematic_V1.0.pdf")

[4] linaro-adfu-tool，[https://github.com/96boards-bubblegum/linaro-adfu-tool/blob/master/src/linaro-adfu-tool-bg96.c](https://github.com/96boards-bubblegum/linaro-adfu-tool/blob/master/src/linaro-adfu-tool-bg96.c "https://github.com/96boards-bubblegum/linaro-adfu-tool/blob/master/src/linaro-adfu-tool-bg96.c")

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/x_project/s900_hw_adfu.html)。

---
title: "ARM CPU性能实验"
date: 2015-04-09T18:13:27+08:00
url: "/arm-performance-test.html"
gid: "161"
emlog_type: "blog"
summary: "一般工程师的直觉是当提升了CPU的运行频率，那么性能应该是呈现线性的关系，例如如果CPU跑260MHz，当降低到130MHz后，其性能应该会降低一半。实际情况如何呢？我们来做一个实验看看。"
author: "linuxer"
tags: ["ARM性能"]
views: 19631
comment_count: 27
aliases:
  - "/161.html"
---

一、前言

一般工程师的直觉是当提升了CPU的运行频率，那么性能应该是呈现线性的关系，例如如果CPU跑260MHz，当降低到130MHz后，其性能应该会降低一半。实际情况如何呢？我们来做一个实验看看。

二、实验

1、实验环境介绍

硬件平台当然是强大的，生命期超长，死而复生（2010年就phase out了，但仍然有一批人马顽强的在上面开发）的AD6900处理器了。除此之外，还需要一台示波器用来测量时间。

2、在kernel中测试

实验方法如下：   
（1）设置AD6900 ARM core所需的clock（260、130，65，32.5）

（2）使用linux中udelay函数（当然，kernel中udelay是和loops per jiffy相关，我们需要稍加修改，让他仅在260MHz的时候能够正确的delay）的方式进行延时

（3）通过GPIO翻转来确定起始和结束的时间点

（4）用示波器测量方波脉宽，记录实验数据。

实验结果如下：

|  |  |
| --- | --- |
| clock | udelay的执行时间 |
| 260 | 2.5ms |
| 130 | 5.0ms |
| 65 | 10ms |
| 32.5 | 20ms |

基本上，在260MHz中执行2.501ms的程序，在130MHz上执行了5.081ms的时间，在32.5MHz上执行了20.64ms，基本上CPU运行clock和程序执行时间呈现线性的关系。

3、在bootloader中测试

同样的实验，我们在bootloader中重复进行，udelay有两个版本，一个是c语言的版本，一开始代码如下：

> void delay( void )   
> {   
> int cnt = 20000;   
> while(cnt—);   
> }

编译之后，delay函数没有任何效果。当然由于开了O2的优化，实际上上面的函数都被优化掉了，要不改成全局变量试一试：

> int cnt = 20000;   
> void delay( void )   
> {   
> while(cnt--);   
> }

情况依然，由于强大的编译器知道delay函数执行到最后cnt等于－1，因此，在delay函数中就偷懒，直接给cnt赋值－1，优化掉了--操作和while判断，当然，给cnt变量加上volatile的修饰符应该是OK了，我们采用了简单的去掉O2优化的方法，得到了下面的结果：

|  |  |
| --- | --- |
| clock | udelay的执行时间 |
| 260 | 2.610ms |
| 130 | 3.720ms |
| 65 | 4.630ms |
| 32.5 | 9.242ms |

好象结果已经不是那么线性了。怎么回事，要不用汇编写，这样会更直接一些，代码如下：

> 400202f4 <\_\_delay>:   
> 400202f4: e2500001 subs r0, r0, #1 ; 0x1   
> 400202f8: 8afffffd bhi 400202f4 <\_\_delay>

当然，在执行\_\_delay函数之前，要传递初值给r0寄存器。OK，代码已经完全和linux中的一致了，测试结果如下：

|  |  |
| --- | --- |
| clock | udelay的执行时间 |
| 260 | 2.5ms |
| 130 | 2.5ms |
| 65 | 2.5ms |
| 32.5 | 5ms |

呵呵，结果多么的神奇。

三、分析

1、和程序执行相关的HW block如下图所示：

[![cpu block](/content/uploadfile/201504/06804468f393a81db7d21b0cb5cfe3b620150409101221.gif "cpu block")](/content/uploadfile/201504/056b277eb3bd5305ed2a0afd59cfa81020150409101109.gif)

上图只是画出和本次实验有关的block。

2、kernel中的程序执行过程描述

内核态的delay函数虽然代码位于SDRAM，但是由于：

（1）TLB已经保存了地址映射

（2）指令已经被加载到cacheline

因此，实际上程序的执行基本是是限制在了ARM core内，不需要通过bus访问类似SRAM或者SDRAM的bus slave设备。这时候，增加ARM core的频率可以获取线性的程序性能提升。

3、bootloader中的程序执行过程描述

由于种种原因，我们的bootload中没有打开cache，没有启动MMU，而且bootloader中的代码在System RAM中运行。具体clock配置如下：

|  |  |  |
| --- | --- | --- |
| ARM clock | BUS clock | udelay的执行时间 |
| 260 | 65 | 2.5ms |
| 130 | 65 | 2.5ms |
| 65 | 65 | 2.5ms |
| 32.5 | 32.5 | 5ms |

由于ARM core需要每次去system RAM中取指，虽然ARM core可以运行在260MHz下，但是由于BUS block限制在65MHz上，因此，大部分的时间，ARM core处于饥饿状态，这种状态下，什么流水线、什么out-of-order，什么分支预测都是浮云，性能的瓶颈来自上图中的A bus。因此，在260、130和65MHz下得到了相同的测试结果。

我们再来看看c代码版本的情况，使用objdump看看实际执行的代码是怎样的：

> 400202b0: e59f3028 ldr r3, [pc, #40] ; 400202e0 <.text+0x2e0>   
> 400202b4: e5933000 ldr r3, [r3]   
> 400202b8: e2432001 sub r2, r3, #1 ; 0x1   
> 400202bc: e59f301c ldr r3, [pc, #28] ; 400202e0 <.text+0x2e0>   
> 400202c0: e5832000 str r2, [r3]   
> 400202c4: e59f3014 ldr r3, [pc, #20] ; 400202e0 <.text+0x2e0>   
> 400202c8: e5933000 ldr r3, [r3]   
> 400202cc: e3730001 cmn r3, #1 ; 0x1   
> 400202d0: 1afffff6 bne 400202b0

汇编代码就2条指令，反复执行，c版本的看起来要复杂多了。为何c版本的delay函数没有出现和汇编版本的delay一样的测试结果呢？（TODO，我们留给大家思考吧）

PS：能完成这篇文档，我首先要感谢CCTV，MTV，各种TV，还有华南区linux kernel首席团队的LGR同学，多谢他的实验数据。

*原创文章，转发请注明出处。蜗窝科技*

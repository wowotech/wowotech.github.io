---
title: "ARM概念梳理：Architecture, Core, CPU，SOC"
date: 2014-12-09T22:54:05+08:00
url: "/armv8a_arch/arm_concept.html"
gid: "119"
emlog_type: "blog"
summary: "本文简单梳理一下ARM有关的概念，包括ARM architecture、ARM core、ARM&nbsp;CPU（或MCU）以及ARM Soc。我们这些以ARM平台为主的嵌入式工程师，几乎每天都会和这些概念打交道，也似乎非常理解它们。但仔细想想，却有些说不清道不明的感觉，因而有必要整理一下思路，也就顺手记录下来了。"
author: "wowo"
category: "ARMv8A Arch"
category_alias: "armv8a_arch"
tags: ["Architecture", "ARM", "core", "soc"]
views: 31427
comment_count: 11
aliases:
  - "/armv8a_arch/119.html"
  - "/119.html"
---

#### 1. 前言

本文简单梳理一下ARM有关的概念，包括ARM architecture、ARM core、ARM CPU（或MCU）以及ARM Soc。我们这些以ARM平台为主的嵌入式工程师，几乎每天都会和这些概念打交道，也似乎非常理解它们。但仔细想想，却有些说不清道不明的感觉，因而有必要整理一下思路，也就顺手记录下来了。

#### 2. 概念梳理

1）ARM architecture

ARM architecture，是指ARM公司开发的、基于精简指令集架构（RISC, Reduced Instruction Set Computing architecture）的指令集架构（Instruction set architecture）。我们常说的ARMv7、ARMv8、ARMv8-A，就是指ARM architecture。类似的基于RISC的architecture也有很多，例如MIPS、AVR、Blackfin等等，都是这个概念。

2）ARM core

ARM core是基于ARM architecture开发出来的IP core，它是介于architecture和最终的CPU(MCU)之间的中间产品，这也是ARM商业模式的独特之处。

有两种类型的ARM core：一种是ARM公司自己发布的，如我们耳熟能详的ARM7、ARM9、ARM Cortex M3、ARM Cortex A57等等；另一种是ARM授权其它公司开发的Core，如苹果的A6/A6X等等。下面链接是维基百科上的ARM core的列表，共大家参考：

[http://en.wikipedia.org/wiki/List\_of\_ARM\_microarchitectures](http://en.wikipedia.org/wiki/List_of_ARM_microarchitectures "http://en.wikipedia.org/wiki/List_of_ARM_microarchitectures")

3）ARM CPU（MCU）

其它的芯片厂商，如Phillips、ST、TI等，会基于ARM公司发布的Core，开发自己的ARM处理器，这称作ARM CPU（也可称为MCU）。这些是我们工作过程中接触最多的，如LPCxxxx、STM32xxx、OMAPxxxx、S3Cxxxx等等。

4）ARM Soc

对于一些比较专业的应用场景，如视频、音频等，为了追求更小的size、更低的功耗，厂商会在芯片上，集成除处理器之外的东西，如视频编解码器、DSP等。这些集成了其它功能的芯片，称作片上系统（SOC），如TI的DM37x Video SOC。

注1：其实ARM的技术和商业模式，正体现了软件工程中抽象和封装的思想。

#### 3. ARM 64bit

我们以一款64bit ARM CPU为例，反向阐述一下ARM处理的诞生过程，同时罗列一些学习、研究方向。

1）我们熟悉一个CPU（假设它的型号是WW9000）的第一手资料，是芯片厂家发布的Datasheet，例如WW9000\_SPEC.pdf。

2）WW9000是基于ARM Cortex-A57 Core封装而来的，该ARM core的资料可以从下面链接下载

[http://infocenter.arm.com/help/topic/com.arm.doc.ddi0488g/DDI0488G\_cortex\_a57\_mpcore\_trm.pdf](http://infocenter.arm.com/help/topic/com.arm.doc.ddi0488g/DDI0488G_cortex_a57_mpcore_trm.pdf "PDF version")

3）ARM Cortex-A57 Core又是基于ARMv8-A architecture，该结构的资料可以通过如下方式获取：

Go to [ARM Infocenter](http://infocenter.arm.com/) and navigate through *ARM architecture* / *Reference Manuals*

注2：[ARM Infocenter](http://infocenter.arm.com/)中资料是非常全面的，没事时可以多逛逛。

*原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/armv8a_arch/arm_concept.html)。*

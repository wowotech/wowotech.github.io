---
title: "ARMv8-a架构简介"
date: 2015-07-07T22:31:00+08:00
url: "/armv8a_arch/armv8-a_overview.html"
gid: "198"
emlog_type: "blog"
summary: "\r\n\tARMv8（当前只有A系列，即ARMv8-A）架构，是ARM公司为满足新需求而重新设计的一个架构，是近20年来，ARM架构变动最大的一次。它引入的Execution State、Exception Level、Security State等新特性，已经和我们对旧的ARM架构的认知，有很大差距了。\r\n\r\n\r\n\t因此，本文从ARMv8-A产生的背景开始，对它进行一个简单的介绍，使大家从整体上，对"
author: "wowo"
category: "ARMv8A Arch"
category_alias: "armv8a_arch"
tags: ["arm64", "armv8-a", "exception_level;security;virtualization"]
views: 94857
comment_count: 37
aliases:
  - "/armv8a_arch/198.html"
  - "/198.html"
---

#### 1. 前言

ARMv8（当前只有A系列，即ARMv8-A）架构，是ARM公司为满足新需求而重新设计的一个架构，是近20年来，ARM架构变动最大的一次。它引入的Execution State、Exception Level、Security State等新特性，已经和我们对旧的ARM架构的认知，有很大差距了。

因此，本文从ARMv8-A产生的背景开始，对它进行一个简单的介绍，使大家从整体上，对ARMv8有一个简单的了解。

#### 2. 背景

本节参考自“<http://www.arm.com/zh/files/downloads/ARMv8_white_paper_v5.pdf>”，感兴趣的同学可以自行阅读。

有一点是可以确定的，ARM诞生时，对Intel主导的PC市场，没有（也不敢有）一点点的非分之想。最初的ARMv4（ARM7系列），到最近的ARMv7（Cortex-A,-M,-R系列），都是针对功耗比较敏感的移动设备的，就性能而言，基于ARM处理器的设备，始终无法和PC相提并论。

但从ARMv7开始，情况开始有些转变，ARM的市场开始扩展到移动设备之外的其它领域，这也是ARMv7划分为A（Application）、R（Real-time）和M（Microcontroller）三个系列的原因，其实质就是三个细分市场，其中的A系列，就是针对性能要求较高的应用。

特别是在Cortex-A9之后，ARM的处理性能有很大的提高，渐渐的吸引了一些PC用户。因此基于ARM的类PC产品，如平板电脑，开始大量涌现。此时，ARM的处理能力，已经有机会应用于其它领域了，如企业设备、服务器等，当然，其优势依然是低功耗。

与此同时，新的趋势正在酝酿，主要包括大内存（Large Memory）、虚拟化（Virtualization）和安全（Security）。Virtualization在ARMv7上已经有简单的硬件实现，Security也有可能基于当前架构扩展，唯有Large memory的需求，有点棘手。

由于处理器性能越来越强，运行于其上的软件也来越复杂，复杂到单一应用对内存的需求可能超出32-bit架构所能支持的最大内存（4G），这就是Large memory需求的起因。不过，后来的Cortex-A15（ARMv7架构）通过Large Physical Address Extensions (LPAE) 技术，可以支持高达40bits的物理地址空间。但受限于32-bit的指令集，虚拟地址空间依旧只有32bits（4G），如果有应用需要更大的虚拟内存，怎么办？只能定义一个新的架构，使用64-bit的指令集（也即我们常说的ARM64）。

毫无疑问，在现阶段，需要超过4G虚拟内存的应用场景，是非常少的。但ARM还是定义了一个新的架构--ARMv8，为什么呢？下面是ARM的解释（只有伟大的公司才有伟大的理念！）：

> Trends. That’s really what ARM has to look at when defining a new architecture. That is the nature of our business, we need to look a long way forward, and plan.

当然，ARMv8并不仅仅是为了解决虚拟地址的问题，它也要解决现有架构的一些问题。不过，新的问题又来了：一个新的架构？用户为什么要使用新的架构？因此，ARMv8的定义，必须先满足如下前提条件：

> 1）对上兼容。
>
> 2）能解决现存架构的已知问题。
>
> 3）相比现存架构，必须具备优势明显的新特性，哪怕软件从来不使用这些新特性。

以上就是ARMv8-a产生的背景，也是ARMv8-a架构之所以是“这个”样子的直接原因。那么到底是什么样子呢？我们继续介绍。

#### 3. ARMv8-a架构简介

基于上面的前提条件，ARMv8-a架构的主要特性包括：

1）新增一套64-bit的指令集，称作A64。

2）由于需要向前兼容ARMv7，所以同时支持现存的32-bit指令集，称作A32和T32（也即我们熟悉的ARM和Thumb指令集）。

3）定义AArch64和AArch32两套运行环境（称作Execution state），分别执行64-bit和32-bit指令集。软件可以在需要的时候，切换Execution state。

4）AArch64最大的改动，使用新的概念（exception level），重新解释了processor mode、privilege level等概念，具体可参考第4章的介绍。

5）在ARMv7 security extension的基础上，新增security model，支持安全相关的应用需求。

6）在ARMv7 virtualization extension的基础上，提供完整的virtualization框架，从硬件上支持虚拟化。

#### 4. AArch64 Exception level

Exception level，是ARMv8-a引入的一个新概念，用于整合之前架构中processor mode和privilege level相关的功能。

**4.1 ARMv7之前的实现**

我们知道，以前的ARM架构，处理器可以工作在多种模式（称作processor mode）下，包括User、FIQ、IRQ、Abort、Undefined、System等，之所以存在不同的模式，主要有2个方面的考虑：

> 1）不同的处理器模式，有不同的硬件访问权限，称作privilege level。
>
> 主要有2个level，privilege和non-privilege。其中只有User模式属于non-privilege level，其它均是privilege level。
>
> 安全起见，大多数时候，软件都运行在User mode。一旦需要其它操作，则需要切换到相应的privilege模式下。这是最原始、最朴素的安全思想，当然，只防君子，不防小人。
>
> 2）这些处理器模式，除User模式外，其它模式基本上和各类异常一一对应。而不同的模式，都有一些自己独有的寄存器，例如R13(SP)、R14(LR)等等，可以使模式切换过程（也是异常处理过程）更为高效、便利。

**4.2 ARMv7-a的实现**

ARMv7-a基本保留了之前的设计，不同之处，将privilege level命名了，称作PL0和PL1（也许您猜到了，后来出现了PL2，用于虚拟化扩展（Virtualization Extension）。

另外，增加了两个模式：Monitor和Supervisor，分别用于security扩展和virtualization扩展。

**4.3 ARMv8-a的实现**

可能ARMv8-a的设计者觉得之前的设计有些啰嗦，就把processor mode的概念去掉（或者说淡化）了，取而代之的是4个固定的Exception level，简称EL0-EL3。同时，也淡化了privilege level的概念。Exception level本身就已经包好了privilege的信息，即ELn的privilege随着n的增大而增大。类似地，可以将EL0归属于non-privilege level，EL1/2/3属于privilege level。

这些Exception level的现实意义是（如下图，先忽略Secure model有关的内容）：

[![aarch32_exception_levels](/content/uploadfile/201507/90b488a2378e7792f7cf5067541c0b2b20150707143059.gif "aarch32_exception_levels")](/content/uploadfile/201507/7ffa71881f6356c740ef254b01cecf1520150707143059.gif)

> ARMv8-a Exception level有关的说明如下：
>
> 1）首先需要注意的是，AArch64中，已经没有User、SVC、ABT等处理器模式的概念，但ARMv8需要向前兼容，在AArch32中，就把这些处理器模式map到了4个Exception level。
>
> 2）Application位于特权等级最低的EL0，Guest OS（Linux kernel、window等）位于EL1，提供虚拟化支持的Hypervisor位于EL2（可以不实现），提供Security支持的Seurity Monitor位于EL3（可以不实现）。
>
> 3）只有在异常发生时（或者异常处理返回时），才能切换Exception level（这也是Exception level的命名原因，为了处理异常）。当异常发生时，有两种选择，停留在当前的EL，或者跳转到更高的EL，EL不能降级。同样，异常处理返回时，也有两种选择，停留在当前EL，或者调到更低的EL。
>
> 注1：有关ARMv8-a异常处理的具体细节，会在其它文章中描述。

#### 5. security model

ARMv8-a的security模型基本沿用了ARMv7 security extension的思路，主要目的保护一些安全应用的数据，例如支付等。它不同于privilege level等软件逻辑上的保护，而是一种物理上的区隔，即不同security状态下，可以访问的物理内存是不同的。

ARMv8-a架构有两个security state（参考上面图片），Security和non-Security。主要的功效是物理地址的区隔，以及一些system control寄存器的访问控制：

> 在Security状态下，处理器可以访问所有的Secure physical address space以及Non-secure physical address space；
>
> 在Non-security状态下，只能访问Non-secure physical address space，且不能访问Secure system control resources。

#### 6. virtualization

硬件虚拟化包括指令集虚拟化、异常处理虚拟化、MMU虚拟化、IO虚拟化等多个议题，比较复杂，这里先不描述了。

#### 7. 总结

本文简单介绍了ARMv8-a中的一些概念，后续文章将会重点关注异常处理模型、security模型、virtualization模型。

*原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/armv8a_arch/armv8-a_overview.html)。*

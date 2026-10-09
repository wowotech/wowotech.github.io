---
title: "Linux DMA Engine framework(1)_概述"
date: 2017-03-30T22:01:37+08:00
url: "/linux_kenrel/dma_engine_overview.html"
gid: "389"
emlog_type: "blog"
summary: "前面文章介绍“ Linux MMC framework ”的时候，涉及到了MMC数据传输，进而不可避免地遭遇了DMA(Direct Memory Access)。因而，择日不如撞日，就开几篇文章介绍Linux的DMA Engine framework吧。 本文是DMA Engine framework分析文章的第一篇，主要介绍DMA controller的概念、术语（从硬件的角度，大部分翻译自ke"
author: "wowo"
category: "Linux内核分析"
category_alias: "linux_kenrel"
tags: ["Linux", "Kernel", "内核", "framework", "dma", "engine"]
views: 40081
comment_count: 14
aliases:
  - "/linux_kenrel/389.html"
  - "/389.html"
---

## 1. 前言

前面文章介绍“[Linux MMC framework](/tag/mmc)”的时候，涉及到了MMC数据传输，进而不可避免地遭遇了DMA(Direct Memory Access)。因而，择日不如撞日，就开几篇文章介绍Linux的DMA Engine framework吧。

本文是DMA Engine framework分析文章的第一篇，主要介绍DMA controller的概念、术语（从硬件的角度，大部分翻译自kernel的document[1]）。之后，会分别从Provider（DMA controller驱动）和Consumer（其它驱动怎么使用DMA传输数据）两个角度，介绍Linux DMA engine有关的技术细节。

## 2. DMA Engine硬件介绍

DMA是Direct Memory Access的缩写，顾名思义，就是绕开CPU直接访问memory的意思。在计算机中，相比CPU，memory和外设的速度是非常慢的，因而在memory和memory（或者memory和设备）之间搬运数据，非常浪费CPU的时间，造成CPU无法及时处理一些实时事件。因此，工程师们就设计出来一种专门用来搬运数据的器件----DMA控制器，协助CPU进行数据搬运，如下图所示：

[![dma](/content/uploadfile/201703/761a9244e7916bc8000a8f79dab9669a20170330140311.gif "dma")](/content/uploadfile/201703/ed79a6952349c83c0a1c9993fdc0fa3b20170330140311.gif)

图片1 DMA示意图

思路很简单，因而大多数的DMA controller都有类似的设计原则，归纳如下[1]。

注1：得益于类似的设计原则，Linux kernel才有机会使用一套framework去抽象DMA engine有关的功能。

#### 2.1 DMA channels

一个DMA controller可以“同时”进行的DMA传输的个数是有限的，这称作DMA channels。当然，这里的channel，只是一个逻辑概念，因为：

> 鉴于总线访问的冲突，以及内存一致性的考量，从物理的角度看，不大可能会同时进行两个（及以上）的DMA传输。因而DMA channel不太可能是物理上独立的通道；
>
> 很多时候，DMA channels是DMA controller为了方便，抽象出来的概念，让consumer以为独占了一个channel，实际上所有channel的DMA传输请求都会在DMA controller中进行仲裁，进而串行传输；
>
> 因此，软件也可以基于controller提供的channel（我们称为“物理”channel），自行抽象更多的“逻辑”channel，软件会管理这些逻辑channel上的传输请求。实际上很多平台都这样做了，在DMA Engine framework中，不会区分这两种channel（本质上没区别）。

#### 2.2 DMA request lines

由图片1的介绍可知，DMA传输是由CPU发起的：CPU会告诉DMA控制器，帮忙将xxx地方的数据搬到xxx地方。CPU发完指令之后，就当甩手掌柜了。而DMA控制器，除了负责怎么搬之外，还要决定一件非常重要的事情（特别是有外部设备参与的数据传输）：

> 何时可以开始数据搬运？

因为，CPU发起DMA传输的时候，并不知道当前是否具备传输条件，例如source设备是否有数据、dest设备的FIFO是否空闲等等。那谁知道是否可以传输呢？设备！因此，需要DMA传输的设备和DMA控制器之间，会有几条物理的连接线（称作DMA request，DRQ），用于通知DMA控制器可以开始传输了。

这就是DMA request lines的由来，通常来说，每一个数据收发的节点（称作endpoint），和DMA controller之间，就有一条DMA request line（memory设备除外）。

最后总结：

> DMA channel是Provider（提供传输服务），DMA request line是Consumer（消费传输服务）。在一个系统中DMA request line的数量通常比DMA channel的数量多，因为并不是每个request line在每一时刻都需要传输。

#### 2.3 传输参数

在最简单的DMA传输中，只需为DMA controller提供一个参数----transfer size，它就可以欢快的工作了：

> 在每一个时钟周期，DMA controller将1byte的数据从一个buffer搬到另一个buffer，直到搬完“transfer size”个bytes即可停止。

不过这在现实世界中往往不能满足需求，因为有些设备可能需要在一个时钟周期中，传输指定bit的数据，例如：

> memory之间传输数据的时候，希望能以总线的最大宽度为单位（32-bit、64-bit等），以提升数据传输的效率；   
> 而在音频设备中，需要每次写入精确的16-bit或者24-bit的数据；   
> 等等。

因此，为了满足这些多样的需求，我们需要为DMA controller提供一个额外的参数----transfer width。

另外，当传输的源或者目的地是memory的时候，为了提高效率，DMA controller不愿意每一次传输都访问memory，而是在内部开一个buffer，将数据缓存在自己buffer中：

> memory是源的时候，一次从memory读出一批数据，保存在自己的buffer中，然后再一点点（以时钟为节拍），传输到目的地；   
> memory是目的地的时候，先将源的数据传输到自己的buffer中，当累计一定量的数据之后，再一次性的写入memory。

这种场景下，DMA控制器内部可缓存的数据量的大小，称作burst size----另一个参数。

#### 2.4 scatter-gather

我们在“[Linux MMC framework(2)\_host controller driver](/comm/mmc_host_driver.html)”中已经提过scatter的概念，DMA传输时也有类似概念：

> 一般情况下，DMA传输一般只能处理在物理上连续的buffer。但在有些场景下，我们需要将一些非连续的buffer拷贝到一个连续buffer中（这样的操作称作scatter gather，挺形象的）。
>
> 对于这种非连续的传输，大多时候都是通过软件，将传输分成多个连续的小块（chunk）。但为了提高传输效率（特别是在图像、视频等场景中），有些DMA controller从硬件上支持了这种操作。   
> 注2：具体怎么支持，和硬件实现有关，这里不再多说（只需要知道有这个事情即可，编写DMA controller驱动的时候，自然会知道怎么做）。

## 3. 总结

本文简单的介绍了DMA传输有关的概念、术语，接下来将会通过下面两篇文章，介绍Linux DMA engine有关的实现细节：

> Linux DMA Engine framework(2)\_provider
>
> Linux DMA Engine framework(3)\_consumer

## 4. 参考文档

[1] Documentation/dmaengine/provider.txt

*原创文章，转发请注明出处。蜗窝科技*，[www.wowotech.net](/linux_kenrel/dma_engine_overview.html)。

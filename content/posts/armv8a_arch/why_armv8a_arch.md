---
title: "为什么会有“ARMv8A Architecture”这个分类"
date: 2014-12-06T15:40:14+08:00
url: "/armv8a_arch/why_armv8a_arch.html"
gid: "117"
emlog_type: "blog"
summary: "2013年9月11日（是的，911），在ARM公司发布UEFI 64-bit之后，ARM社区release了ARMv8A版本的ARM Architecture Reference Manual（我已经下载，感兴趣的同学可以找我要）。在 release note 中，作者给出了这样一个设问句：“Why develop ARMv8-A?”。本文也效仿一下，以自问自答的形式，说明为什么会在博客中增加这样"
author: "wowo"
category: "ARMv8A Arch"
category_alias: "armv8a_arch"
tags: ["Architecture", "arm64", "aarch64", "armv8-a"]
views: 19509
comment_count: 16
aliases:
  - "/armv8a_arch/117.html"
  - "/117.html"
---

2013年9月11日（是的，911），在ARM公司发布UEFI 64-bit之后，ARM社区release了ARMv8A版本的ARM Architecture Reference Manual（我已经下载，感兴趣的同学可以找我要）。在[release note](http://community.arm.com/groups/processors/blog/2013/10/09/arm-architecture-reference-manual-for-armv8-a-64-bit-publicly-released)中，作者给出了这样一个设问句：“Why develop ARMv8-A?”。本文也效仿一下，以自问自答的形式，说明为什么会在博客中增加这样一个分类，以及期望达成的目的。

添加“ARMv8A Architecture”这个分类的原因包括：

1）自从ARM64bit（即ARMv8-A，也称作AARCH64）发布以来，linuxer、forion、wowo等同学，都表现除了极大的兴趣，希望能对它有个比较系统的了解。

2）未来的一段时间内，wowotech主要会focus在Linux内核分析上，由于我们的工作性质，一般都会基于ARM平台分析。kernel的很多模块，如进程管理、内存管理、中断管理、timer管理、cpuidle、cpufreq、spinlock等等，和体系结构的相关性非常大。以前的做法，是在相应的分析文章中，穿插介绍体系结构的内容。但这种做法比较零碎，不成体系，也很难理解。因而希望将ARM体系结构先关的知识，汇整在一起。

3）近些年，ARM发展很快，从最初的ARM7/ARM9（v4T或v5E），到后来的ARM11（v6），以及现在比较流行的Cortex系列（v7/v8/v8-A）。虽然ARM基本架构还维持不变，但却有非常多的新知识点。而我们这些从ARM7开始做起的“老人”，已经有很多年没有进行头脑风暴了。

4）ARMv8-A作为ARM第一款64bit的架构，在增加64bit的诸多特性的同时，保持了向前兼容，那么拿它做分析对象，就再好不过了。

5）从另一个角度看，当初的ARM7还是以“单片机”的形式出现的，在那个年代，没有强大的OS、没有复杂的软件抽象和软件分工，这就要求嵌入式软件开发人员有非常扎实的硬件功底，因而要非常熟悉ARM体系结构，这也是《ARM体系结构和编程》畅销的原因。但现在就不同了，一个Android下的Linux driver开发者，甚至不需要知道体系结构的存在……那这种现象好不好呢？从产业的角度看，好；从技术的角度看，不好！

6）wowotech的理念是享受技术，那么怎么能放过体系结构这一块肥肉呢？

理想虽然很丰满，但现实却很骨感，我们没有那么多时间，系统的去理解、分析并分享这些知识。但做总比不做好，这个分类下面的文章的基调是：Linux内核分析到某个模块（如cpuidle），需要用到体系结构的知识，就在这里记录下来。希望能积少成多，或许有一天，可以出一版新的《ARM体系结构与编程》，说不定呢！

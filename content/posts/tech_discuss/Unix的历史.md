---
title: "Unix的历史"
date: 2014-04-21T20:32:07+08:00
url: "/tech_discuss/Unix的历史.html"
gid: "33"
emlog_type: "blog"
summary: "\r\n\t作为一个Linuxer，对unix感兴趣是顺理成章的事情，对unix的了解反过来也可以促进对GNU/Linux的理解。不过在接触unix的过程中，大家一般都会有下面的疑问：\r\n\r\n\r\n\t1、unix这个商标是属于哪一个公司或者机构？\r\n\r\n\r\n\t2、为何unix有那么多的变种？为何各个公司都有自己的unix，例如IBM的AIX（Advanced Interactive eXecutive）操"
author: "linuxer"
category: "技术漫谈"
category_alias: "tech_discuss"
tags: ["unix历史"]
views: 19052
comment_count: 8
aliases:
  - "/tech_discuss/33.html"
  - "/33.html"
---

一、前言

作为一个Linuxer，对unix感兴趣是顺理成章的事情，对unix的了解反过来也可以促进对GNU/Linux的理解。不过在接触unix的过程中，大家一般都会有下面的疑问：

1、unix这个商标是属于哪一个公司或者机构？

2、为何unix有那么多的变种？为何各个公司都有自己的unix，例如IBM的AIX（Advanced Interactive eXecutive）操作系统、SUN公司的Solaris操作系统、HP公司的HP-UX操作系统。

3、Linux和unix的关系为何？

……

本文和技术无关，主要想整理一些Unix的历史和Linux的演化

二、Unix的诞生

1969年的8月份，在老婆带着孩子回娘家后，AT&T公司Bell实验室的宅男程序员Ken Thompson花费了一个月的时间，使用汇编语言开发了第一个版本的unix，并将它运行在DEC公司的PDP-7的小型机上。这样的成果当然不是凭空产生，Thompson 和Dennis Ritchie作为Bell实验室的代表，参与了MULTICS项目。该项目是一个MIT、GE和Bell实验室的联合项目，旨在提供一个时分操作系统。在Bell实验室退出该项目后，Thompson变得无所事事（特别是老婆孩子又不在身边），反正闲着也是闲着，于是写出了第一个版本的unix。

unix这个名字源自MULTICS（Multiplexed Information and Computing Service），Thompson认为MULTICS是一个overdesigned and overbuilt and over everything的操作系统，他本人认为优秀的操作系统的特点应该是简单、优雅和易用。在这样的思路指引下，这个简介的OS被命名为Unics (Uniplexed Information and Computing Service)，后续被修正为unix。

当然，一个人的力量是有限的，Thompson以及他的同事都加入了这个unix操作系统的开发。特别是在Dennis Ritchie发明了c语言之后，unix用c语言重写一遍。虽然当时已经存在了FORTRAN和COBOL这样的高级语言，但并不适合开发unix操作系统。c语言的发明是和unix相关的，开发unix需要一个适合unix kernel及其系统软件的高级语言工具，没有适合的工具，unix开发团队只能自己创造。在Thompson 和Dennis Ritchie的带领下，unix开发团队在1969到1979年之间release了若干用数字标识的版本。First Edition，Second Edition……Seventh Edition。本来，unix这点事都是AT&T公司内部的事，不过1974年，Dennis Ritchie和Thompson在CACM上发表了论文：The UNIX Time-Sharing System，这一下子，unix成了尽人皆知的秘密了。

本来，AT&T公司成立Bell实验室进行一些前瞻性的研究，最终当然是想转化为产品，对于Unix也不例外。然而，在当时，AT&T公司和美国政府签署了美国电话业务的专营协议，该协议规定AT&T不能从事软件销售业务，也就是说，AT&T公司不能把Unix当作一个产品来销售。因此，从Sixth Edition开始，AT&T将unix分发给美国的大学（当然，也收取了distribution fee），这些分发给大学的发布包里面包含了文档和unix kernel的source code。

三、BSD和System V

Thompson 在1975/1976学年来到了加州伯克利分校做客座教授，并且带了些研究生一起继续进行Unix的后续开发，在伯克利，很多新的特性加入到了unix操作系统中，并发布了一些早期的BSD版本。这些BSD版本引起了Defense Advanced Research Projects Agency's (DARPA) 的关注，在DARPA的支持下，伯克利的Computer Systems Research Group (CSRG)负责开发 一个标准的unix平台，主要用于DARPA未来的各种研究。BSD (Berkeley Software Distribution)是由加州大学伯克利分校基于AT&T的unix发布包进行二次开发和发布的。BSD为unix带来了很多的新的特性，特别是1983年发布的4.2版本的BSD，该版本实现了TCP/IP协议栈。

与此同时，美国司法部依据《反托拉斯法》对AT&T公司进行拆分。拆分之后，分离出来的公司可以对Unix进行商业化运作，这个从AT&T分离出来的公司就是AT&T USG（Unix Support Group）。USG在1982年release了System III。1983年，Computer Research Group (CRG), UNIX System Group (USG) 连同一起第三方组织成立了UNIX System Development Lab，并发布了System V的第一个版本。1989年System V发布了最后一个版本SVR4。

这样，各大商业计算机制造公司在为自己的硬件平台撰写操作系统的时候就有两种选择，一种是购买商业版本的System V并进行二次开发，另外一种是使用BSD版本的unix进行开发。使用BSD版本进行开发对商业公司是有风险的，因为BSD中包括了AT&T的source code。大部分商业公司选择了前者，也就是基于system V进行开发。例如Sun公司的Sun OS是基于BSD的，随后，Sun公司的OS更名为Solaris，Solaris是基于System V的。IBM的AIX和HP的HP-UX都是基于System V的（AIX虽然是base system V的，但是也引入了4.2和4.3 BSD的source code，其实即便是System V，也会引入一些BSD的特性或者source code）。值得一提的是1980年，Microsoft也从AT&T获得了unix的授权，并发展了Xenix操作系统。后来SCO公司收购了Xenix并更名为SCO unix。

四、unix的版权之争

和AT&T的System V分支不同，BSD版本不是那么focus在商业化Unix上。BSD由大学发布，主要是用于学术研究，希望可以以free software的形式发布。但是，4.3版本以及之前的BSD 中都包括了AT&T的unix code，毫无疑问，这些code应该服从AT&T的license。1991年，CSRG发布了BSD Net/2。它的发布就是为了解决这个问题。在BSD Net/2中，所有AT&T的unix code都被替换或者重写，因此，BSD Net/2是使用BSD license发布的。90年代初，基于Intel公司的CPU的个人PC已经开始流行，386/BSD项目就是将BSD Net/2 porting到386处理器上的一个项目。1992年，386/BSD发布了Version 0.1，之后项目组成员对项目的后续发展产生了分歧，因此386BSD项目分裂成两个项目，freeBSD和NetBSD。freeBSD focus在386平台，主要是修复bug，提高性能。而NetBSD主要想支持更多的硬件平台。openBSD是从NetBSD项目分裂出来的，该项目主要关注系统安全。

没有利益的冲突，也就不会有unix的版权之争了。1991年，CSRG的一些成员开了一家公司，名字是Berkeley Software Design, Inc (BSDI)，BSDI旨在为Intel平台提供商业版本的BSD unix。BSDI贩卖的OS非常便宜，侵犯了USL的利益，1992年，USL将BSDI告上法庭。1994年，USL（这时候USL已经属于Novell公司而非AT&T）和BSDI达成和解：伯克利大学从Net/2 release 的18000个文件中移除3个文件，对一些文件进行简单修改，在70个文件中增加USL的copyright，在这些条件下，伯克利大学可以继续自由发布。而USL也不会对作出上述修改的软件及其派生软件进行任何权利的追述。1994年，4.4BSD-Lite发布，那些原来BSD Net/2 base的项目都使用了4.4BSD-Lite的源代码，也就不存在版权问题了。

五、结束语

今天，由于GNU/linux的迅猛发展，Unix的前途似乎一片黯淡。Novell从AT&T手中购买了UNIX 但却交给X/open管理，自己则发展了一套命名为UNIXWave 的操作系统。后来unix几经转手，目前属于谁已经不是那么重要了，重要的是，这个在40年前设计的操作系统，其思想在现在仍然闪烁着智慧的光芒。正是由于BSD忙于应付官司而给了linux kernel机会，否则，如果在386有非常优秀的BSD系统的话，Torvalds也许就不会创建linux kernel这个项目。时光飞逝，任何产品，任何公司，任何英雄都是浮浮沉沉，唯有思想存留。作为linuxer，希望能够采颉linux kernel的光芒，分享给大家，一起享受软件的乐趣。

*原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/tech_discuss/Unix%E7%9A%84%E5%8E%86%E5%8F%B2.html)。*

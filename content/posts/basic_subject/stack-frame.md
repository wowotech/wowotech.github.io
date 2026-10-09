---
title: "计算机科学基础知识之（六）：理解栈帧"
date: 2015-03-12T13:00:22+08:00
url: "/basic_subject/stack-frame.html"
gid: "154"
emlog_type: "blog"
summary: "本文以一个简单的例子来描述ARM linux下的stack frame。 本文也是对tigger网友问题的回复。"
author: "linuxer"
category: "基础学科"
category_alias: "basic_subject"
tags: ["stack", "frame", "栈帧"]
views: 25011
comment_count: 8
aliases:
  - "/basic_subject/154.html"
  - "/154.html"
---

一、前言

本文以一个简单的例子来描述ARM linux下的stack frame。

本文也是对tigger网友问题的回复。

二、源代码

> #include <stdio.h>
>
> static int static\_interface\_leaf( int x, int y )   
> {   
> int tmp0 = 0x12;   
> int tmp1 = 0x34;   
> int tmp2 = 0x56;
>
> tmp0 = x;   
> tmp1 = y;
>
> return (tmp0+tmp1+tmp2);   
> }
>
> int public\_interface\_leaf( int x, int y )   
> {   
> int tmp0 = 0x12;   
> int tmp1 = 0x34;   
> int tmp2 = 0x56;
>
> tmp0 = x;   
> tmp1 = y;
>
> return (tmp0+tmp1+tmp2);   
> }
>
> void public\_interface( int x )   
> {   
> int tmp0 = 0x12;   
> int tmp1 = 0x34;
>
> tmp0 = x;   
> public\_interface\_leaf( tmp0, tmp1 );   
> static\_interface\_leaf( tmp0, tmp1 );   
> }
>
> int main(int argc, char \*\*argv)   
> {   
> int tmp0 = 0x12;
>
> public\_interface( tmp0 );
>
> return 0;   
> }

三、逐级stack frame分析

1、准备知识

根据AAPCS的描述，stack是full-descending并且需要满足两种约束：一种是通用约束，适用所有的场景，另外一种是针对public interface的约束。通用约束有3条：

（1）SP只能访问stack base和stack limit之间的memory，即Stack-limit < SP <= stack-base

（2）SP必须对齐在4个字节上，即SP mod 4 = 0

（3）函数只能访问自己能回溯的那些栈帧。例如f1调用f2，而f2函数又调用了f3，那么f3是可以访问自己的stack以及f2和f1的stack，也就是说，函数可以访问[SP, stack-base – 1]之间的内容

对public interface的约束多了一条，就是SP必须对齐在8个字节上，即SP mod 8 = 0

关于ARM的ABI，还有一份文档，IHI0046B\_ABI\_Advisory\_1，这份文件中讲到，在调用所有的AAPCS兼容的函数的时候都要求SP是对齐在8个字节上。

2、起始点的用户栈的情况

在[静态链接](/basic_subject/static-link.html)文档中，我们说过，函数的入口函数不是main函数而是\_start函数，调用序列是\_start()->\_\_libc\_start\_main()->main()。main函数之前对于所有的程序都是一样的，因此不需要每一个程序员都重复进行那些动作，因此留给程序员一个main函数的入口，开始自己相关逻辑的处理。内核在start函数（我在这里以及后面的文档中省略了下划线）之前的stack frame并不是空的，内核会创建一些资料在stack上，具体如下：

![](/content/uploadfile/201502/3a47b6f0c30041e9f67642b3cbf4e87320150216070618.gif)

具体怎么在用户栈上建立上面的数据结构，有兴趣的同学可以参考内核的create\_elf\_tables函数。此外，需要提醒的是这些数据内容虽然在栈上，但是不是stack frame的一部分，有点类似内核空间到用户空间参数传递的味道。为何这么说呢？因为在start函数中有一条汇编指令：mov fp, #0，该指令清除frame pointer，在debugger做栈的回溯的时候，当fp等于0的时候也就意味着到了最外层函数。

3、start函数的start frame

> 0000829c <\_start>:   
> 829c: e59fc024 ldr ip, [pc, #36] ; 82c8 <.text+0x2c>   
> 82a0: e3a0b000 mov fp, #0 ; 0x0－－－－－－－－最外层函数，清除frame pointer   
> 82a4: e49d1004 ldr r1, [sp], #4－－－－－－－－－－r1 = argc, sp=sp+4，sp指向了argv[]   
> 82a8: e1a0200d mov r2, sp－－－－－－－－－－r2保存了stack end，也就是argv[]那个位置   
> 82ac: e52d2004 str r2, [sp, #-4]!－－－－－－－－将stack end压入栈   
> 82b0: e52d0004 str r0, [sp, #-4]!－－－－－－－－将rtld\_fini压入栈   
> 82b4: e59f0010 ldr r0, [pc, #16] ; 82cc <.text+0x30>   
> 82b8: e59f3010 ldr r3, [pc, #16] ; 82d0 <.text+0x34>   
> 82bc: e52dc004 str ip, [sp, #-4]!－－－－－－－－将fini压入栈   
> 82c0: ebffffef bl 8284 <.text-0x18>－－－－－－－call \_\_libc\_start\_main   
> 82c4: ebffffeb bl 8278 <.text-0x24>   
> 82c8: 0000848c .word 0x0000848c   
> 82cc: 00008454 .word 0x00008454   
> 82d0: 00008490 .word 0x00008490

在调用\_\_libc\_start\_main函数之前，stack frame的情况如下：

[![start_sf](/content/uploadfile/201503/5a87d992a4fbfda5ba719a4107b5c4c520150312045255.gif "start_sf")](/content/uploadfile/201503/09b27cb760a7c2827560acb1c0197db420150312045151.gif)

大家可以对照上面的汇编和图片，我这里只是描述基本知识点：

1、stack的确是full-descending的，SP指向了start函数的顶部，下一个函数必须先减SP，才能保存其栈上的数据。

2、内核到用户空间当然是public interface，因此在进入start函数的时候SP当前是8字节对齐。而start函数的栈有3个变量共计12个字节，在调用\_\_libc\_start\_main函数这个public interface的时候当然也要8字节对齐，按理说这里start函数有一个小小的4字节的空洞，但实际上，代码是抹去了用户栈的argc这个参数，因此start的栈的细节如下：

[![ks](/content/uploadfile/201503/3ef3080ba54612b34981a6ce481daabb20150312045500.gif "ks")](/content/uploadfile/201503/0714246a903301c7aa0c673c47775c5020150312045358.gif)

虽然抹去了用户栈的argc这个参数，不过没有关系，反正它已经保存在了r1寄存器中了。

4、\_\_libc\_start\_main函数的stack frame

\_\_libc\_start\_main是libc定义的符号，我们动态链接的时候，这些代码没有进入我们测试的ELF文件。这里略过吧，毕竟查阅c库代码也是非常烦人的事情。

5、main函数的stack frame

> 00008454
>
> :   
>     8454:    e92d4800     stmdb    sp!, {fp, lr}－－－将上一个函数的 fp和lr寄存器压入stack, sp=sp-8   
>     8458:    e28db004     add    fp, sp, #4    ; －－－上一个函数的sp＋4就是本函数stack frame的开始   
>     845c:    e24dd010     sub    sp, sp, #16    ; 0x10   
>     8460:    e1a03000     mov    r3, r0   
>     8464:    e50b1014     str    r1, [fp, #-20]－－－－－－保存argv   
>     8468:    e54b300d     str    r3, [fp, #-16]－－－－－－保存argc   
>     846c:    e3a03012     mov    r3, #18    ; 0x12－－－tmp0 = 0x12，[fp, #-8]就是源代码的tmp0   
>     8470:    e50b3008     str    r3, [fp, #-8]   
>     8474:    e51b0008     ldr    r0, [fp, #-8]－－－－－传递tmp0参数   
>     8478:    ebffffe3     bl    840c    
>     847c:    e3a03000     mov    r3, #0    ; 0x0   
>     8480:    e1a00003     mov    r0, r3   
>     8484:    e24bd004     sub    sp, fp, #4    ; 0x4   
>     8488:    e8bd8800     ldmia    sp!, {fp, pc}

在调用public\_interface之前，main函数的stack frame如下：

[![main_sf](/content/uploadfile/201503/de963c4d87aaeabf711d43e932b2b9d420150312045711.gif "main_sf")](/content/uploadfile/201503/fb507fd5b0e1df6c902bdb333a3912f320150312045605.gif)

对照代码和图片，我们有下面的解释：

（1）第一条指令就是stmdb，这里db就是decrease before的意思，再次确认stack的确是full-descending的

（2）虽然只有一个临时变量tmp0，但是编译器还是传递了argc和argv这两个参数，具体为何我也没有考虑清楚，因此在分配main的stack frame的时候使用了sub sp, sp, #16，分配4个int型数据，当然是为了对齐8字节。

（3）在一个函数的执行过程中，sp和fp之间就是该函数的stack frame。sp指向stack frame的顶部（低地址），fp指向顶部。

（4）由于main函数的fp加4就是\_\_libc\_start\_main的sp，因此在main函数的stack上不需要保存其sp，只要保存fp就OK了。

6、public\_interface的stack frame

> 0000840c :   
> 840c: e92d4800 stmdb sp!, {fp, lr}   
> 8410: e28db004 add fp, sp, #4 ; 0x4   
> 8414: e24dd010 sub sp, sp, #16 ; 0x10   
> 8418: e50b0010 str r0, [fp, #-16]－－－－－－－－－中间变量，保存传入的x参数   
> 841c: e3a03012 mov r3, #18 ; 0x12   
> 8420: e50b300c str r3, [fp, #-12]－－－－－－－－－tmp0 = 0x12   
> 8424: e3a03034 mov r3, #52 ; 0x34   
> 8428: e50b3008 str r3, [fp, #-8]－－－－－－－－－－tmp1 = 0x34   
> 842c: e51b3010 ldr r3, [fp, #-16]   
> 8430: e50b300c str r3, [fp, #-12]－－－－－－－－－tmp0 = x   
> 8434: e51b000c ldr r0, [fp, #-12]   
> 8438: e51b1008 ldr r1, [fp, #-8]   
> 843c: ebffffda bl 83ac    
> 8440: e51b000c ldr r0, [fp, #-12]   
> 8444: e51b1008 ldr r1, [fp, #-8]   
> 8448: ebffffbf bl 834c    
> 844c: e24bd004 sub sp, fp, #4 ; 0x4   
> 8450: e8bd8800 ldmia sp!, {fp, pc}

栈帧情况如下：

[![pli_sf](/content/uploadfile/201503/a669d34714ff667d77f6c8f41562938720150312045918.gif "pli_sf")](/content/uploadfile/201503/88c2b984e5a95c6a2f258fcb91668b5020150312045816.gif)

这里比较简单，大家自行分析就OK了。

7、调用static函数

根据AAPCS的描述，只有public接口才需要SP 8字节对齐。不过测试程序表明所有的都是8字节对齐的，我的编译器关于ABI的缺省设定是-mabi=aapcs-linux，猜想可能是所有的函数都被编译成AAPCS-comforming fuction。具体大家可以自己写代码练习一下。

参考文献

1、AAPCS。Procedure Call Standard for the ARM Architecture

2、IHI0046B\_ABI\_Advisory\_1。ABI for the ARM Architecture Advisory Note – SP must be 8-byte aligned on entry to AAPCS-conforming functions

*原创文章，转发请注明出处。蜗窝科技*

*[/basic_subject/stack-frame.html](/basic_subject/stack-frame.html)*

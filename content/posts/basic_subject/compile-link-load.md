---
title: "计算机科学基础知识（二）:Relocatable Object File"
date: 2015-02-09T19:17:08+08:00
url: "/basic_subject/compile-link-load.html"
gid: "143"
emlog_type: "blog"
summary: "\r\n\t一个合格的c程序员（也可以叫做软件工程师，这样看起来更高大上，当然，我老婆心情不好的时候总是叫我“死打字的”，基本也能描述这份职业，呵呵）\r\n需要理解编译、链接和加载的过程，而不是仅仅关注c语言的语法和词法。本文主要以此为切入点，描述linux系统下，一个普通的hello \r\nworld程序的生命历程，并借机灌输一些程序编译时和运行时的基本术语和概念。当然，由于我本人是一个linuxer，因"
author: "linuxer"
category: "基础学科"
category_alias: "basic_subject"
tags: ["Object", "Relocatable", "File"]
views: 34851
comment_count: 11
aliases:
  - "/basic_subject/143.html"
  - "/143.html"
---

一、前言

一个合格的c程序员（也可以叫做软件工程师，这样看起来更高大上，当然，我老婆心情不好的时候总是叫我“死打字的”，基本也能描述这份职业，呵呵）需要理解编译、链接和加载的过程，而不是仅仅关注c语言的语法和词法。本文主要以此为切入点，描述linux系统下，一个普通的hello world程序的生命历程，并借机灌输一些程序编译时和运行时的基本术语和概念。当然，由于我本人是一个linuxer，因此借用linux来描述这些知识会方便些，但是对于计算机科学而言，这些东西概念上是类似的，只是实现细节不同而已（windows程序员或者其他程序员可以阅读本文哦）。

本文也是阅读了Computer System，A programmer’s perspective的第七章的一个读书笔记，方便日后查阅。注：Computer System，A programmer’s perspective绝对是一本值得反复阅读的书籍，强力推荐。

二、将源代码编译成relocatable object file

1、源代码

计算机科学就是研究0和1的科学，对于程序员，无论是源代码、relocatable object、share object还是可执行程序，都是0和1，不同的是对0和1的解释。对于源代码，其0和1是按照ascii码的格式进行组织，适合人类（主要是程序员）阅读和理解。我们先看看下面这段代码（源文件是hello\_world.c）：

> #include <stdio.h>
>
> int hello\_world\_data = 0x1234;   
> int hello\_world\_bss;
>
> int hello\_world( )   
> {   
> int tmp;
>
> printf("hello world!\n");   
> tmp = hello\_world\_data + hello\_world\_bss;
>
> return tmp;   
> }

一段平淡无奇的代码，甚至有些丑陋。让我们先把它编译成目标文件（使用gcc 4.2.0）：

> arm-linux-gcc –c hello\_world.c

2、relocatable object file

编译的结果就是relocatable object file：hello\_world.o文件。一个203个字节的hello\_world.c源文件为何变成了1208个字节的hello\_world.o文件？还给它起了个relocatable object file的名字？本质上，编译的结果是为了链接，也就是说，hello\_world.o文件必须包含下一步链接需要的信息：

（1）执行代码。源代码虽好，但是只是适合人类阅读，机器阅读还是不适合的。ARM处理器有自己的规则，因此在编译之后，c代码逻辑变成了机器码，可以被处理器解释执行。这些就是.text section

（2）数据。程序的本质是逻辑（控制流）加上数据（数据流），逻辑由.text section提供，而数据部分稍微复杂一些，函数内部的临时变量位于stack上，不在此列，这里的数据是只全局数据，又分成已经初始化的.data section和未初始化的.bss section以及只读数据.rodata section。

（3）定义符号和引用符号的信息。hello\_world.c这个模块定义了若干的符号，这事得让广大人民群众（其他模块）都知道，这样，linker在进行symbol resolution的时候才知道其他模块引用的符号是否是未定义的。同理，hello\_world.c这个模块也要对外宣布，我需要引用哪些符号，你linker要帮忙解析一下，看看其否其他模块有定义该符号。因此，在relocatable object 中存在符号表，即.symtab section。当然，symbol的name的字符串保存在了其他的section，即.strtab中。

（4）由于还没有形成进程的映像，因此relocatable object file中的代码和数据地址都是从0开始的。例如hello\_world这个符号（本质上是一个函数符号）就是位于0地址的，而hello\_world\_data也是位于0地址，如果不对这些符号进行relocation，那么程序是不可能执行起来的。因此，linker需要把若干个relocatable object file（当然还要有库文件）组织成一个可以被加载的image并分配正确的地址给各个符号。为了帮助linker做这件事情，.o文件必须提供relocation information，也就是.rel.text、.rel.data、……

（5）编译器是非常了解目标平台的，相反linker其实没有那么知道target的信息，因此，.o文件也会内嵌这些平台相关信息给linker，以便linker可以更好的工作。

3、动手实验

上节是动手前的思考。一直以来我都是认为这是一个很好的习惯，不要冒然进入，先用基本的逻辑思维思考一下你要观察的对象应该是什么样子的，这个过程中可能会有很多的问题，然后可以带着问题去动手验证。我们进行实验的工具就是bin utilities，命令如下：

> arm-linux-readelf -a hello\_world.o > hello\_world.elf   
> arm-linux-objdump -D -h hello\_world.o > hello\_world.txt

下面，我们的任务就是仔细的观察hello\_world.elf和hello\_world.txt文件

4、观察hello\_world.elf文件和hello\_world.txt文件

（1）概述

实际上无论是relocatable object、share object还是可执行程序都是符合ELF文件格式，ELF文件格式如下图所示：

[![elf](/content/uploadfile/201502/024c029a52e1e56d156964f4c3b195cd20150209111109.gif "elf")](/content/uploadfile/201502/3529cf29b436e4a8ea3926c7839fa30820150209110955.gif)

ELF header是固定位置的header指向具体section header table和program header table。section header table中的每一个entry描述了一个section，并给出该section在ELF文件中的偏移。program header table我们会在后面的章节中解释。

（2）观察.o ELF文件的header

> ELF Header:   
> Magic: 7f 45 4c 46 01 01 01 00 00 00 00 00 00 00 00 00   
> Class: ELF32   
> Data: 2's complement, little endian   
> Version: 1 (current)   
> OS/ABI: UNIX - System V   
> ABI Version: 0   
> Type: REL (Relocatable file)   
> Machine: ARM   
> Version: 0x1   
> Entry point address: 0x0   
> Start of program headers: 0 (bytes into file)   
> Start of section headers: 368 (bytes into file)   
> Flags: 0x4000000, Version4 EABI   
> Size of this header: 52 (bytes) －－－－－ELF 文件的header size   
> Size of program headers: 0 (bytes)   
> Number of program headers: 0   
> Size of section headers: 40 (bytes) －－－－每个section header的size   
> Number of section headers: 12   
> Section header string table index: 9

几个重要的知识点我们可以简单过一下。Type域描述了该ELF文件的类型，REL说明该文件就是一个.o文件，也就是relocatable object file。Machine域描述了该.o文件是for ARM平台的，更详细的平台相关信息可以在特定的section中获取，下面会具体描述。对于一个relocatable object file而言，它是不会被加载运行的，因此其Entry point address是没有意义的，因此等于0。同理，.o文件中也不存在program header。因此Start of program headers、Number of program headers和Size of program headers都等于0。从.o文件的368偏移处是section headers table，其中有12个section header，每个section header entry占用了40个byte，total是12x40=480个字节。

内核中Elf32\_Ehdr和Elf64\_Ehdr这两个datastruct反应了elf header的数据结构。

（3）观察.o文件的section table header

> Section Headers:   
> [Nr] Name Type Addr Off Size ES Flg Lk Inf Al   
> [ 0] NULL 00000000 000000 000000 00 0 0 0   
> [ 1] .text PROGBITS 00000000 000034 000048 00 AX 0 0 4   
> [ 2] .rel.text REL 00000000 000498 000020 08 10 1 4   
> [ 3] .data PROGBITS 00000000 00007c 000004 00 WA 0 0 4   
> [ 4] .bss NOBITS 00000000 000080 000000 00 WA 0 0 1   
> [ 5] .rodata PROGBITS 00000000 000080 000010 00 A 0 0 4   
> [ 6] .comment PROGBITS 00000000 000090 00004d 00 0 0 1   
> [ 7] .note.GNU-stack PROGBITS 00000000 0000dd 000000 00 0 0 1   
> [ 8] .ARM.attributes ARM\_ATTRIBUTES 00000000 0000dd 00002f 00 0 0 1   
> [ 9] .shstrtab STRTAB 00000000 00010c 000061 00 0 0 1   
> [10] .symtab SYMTAB 00000000 000350 000100 10 11 12 4   
> [11] .strtab STRTAB 00000000 000450 000047 00 0 0 1   
> Key to Flags:   
> W (write), A (alloc), X (execute), M (merge), S (strings)   
> I (info), L (link order), G (group), x (unknown)   
> O (extra OS processing required) o (OS specific), p (processor specific)

正如ELF header中描述的那样，section headers table中有12个entry，index 0～11分别标识了这12个section。第一个section是inactive的section，为何这么做后面会描述。.text是程序代码，占据.o文件偏移0x34处，整个长度是0x48。addr域描述运行地址的，.o文件还不具备运行的条件，因此所有section的addr都是0。PROGBITS说明该section包含了程序定义的信息，是属于program的bits。ES是entry size的缩写，有些Section是由一个一个的固定size的item组成，ES描述了这个固定的size，对于.text section而言，当然不是由一个个的条目组成，因此ES等于0。这些section中，.rel.text和.symtab是有固定size的item组成。flag中的A标志说明在程序执行的时候，该section占据memory，正文段、数据段当然是占用memory了，因此有A标记，象符号表、字符串表、重定位信息（.rel.text）这些section，都没有A标记，和程序执行无关，主要是向linker提供后续链接需要的信息。.data的size是4，全局变量hello\_world\_data就位于此section。hello\_world\_bss对应.bss section，当然，由于它是未初始化的全局变量，因此在.o文件中没有它的位置，.bss section的size是0。.bss section被标记了NOBITS，这个标记含义和PROGBITS一样，只不过它不占用.o 文件的size。数据段（.data .bss）都是有W标记，说明该section是可写的。.rodata对应常量字符串hello world!\n，size域显示该section的长度是16，当然，这个常量字符串没有那么长，只不过由于这个section是按照4字节对齐的（Al就是align，标识该section的字节对齐单位），因此长度是16。

内核中Elf32\_Shdr和Elf64\_Shdr这两个data struct反应了section header的数据结构。

（4）观察.o文件的符号表

> Symbol table '.symtab' contains 16 entries:   
> Num: Value Size Type Bind Vis Ndx Name   
> 0: 00000000 0 NOTYPE LOCAL DEFAULT UND   
> 1: 00000000 0 FILE LOCAL DEFAULT ABS hello\_world.c－－－对应的source code file   
> 2: 00000000 0 SECTION LOCAL DEFAULT 1   
> 3: 00000000 0 SECTION LOCAL DEFAULT 3   
> 4: 00000000 0 SECTION LOCAL DEFAULT 4   
> 5: 00000000 0 NOTYPE LOCAL DEFAULT 3 $d   
> 6: 00000000 0 SECTION LOCAL DEFAULT 5   
> 7: 00000000 0 NOTYPE LOCAL DEFAULT 1 $a   
> 8: 0000003c 0 NOTYPE LOCAL DEFAULT 1 $d   
> 9: 00000000 0 SECTION LOCAL DEFAULT 7   
> 10: 00000000 0 SECTION LOCAL DEFAULT 6   
> 11: 00000000 0 SECTION LOCAL DEFAULT 8   
> 12: 00000000 4 OBJECT GLOBAL DEFAULT 3 hello\_world\_data   
> 13: 00000000 72 FUNC GLOBAL DEFAULT 1 hello\_world   
> 14: 00000000 0 NOTYPE GLOBAL DEFAULT UND puts   
> 15: 00000004 4 OBJECT GLOBAL DEFAULT COM hello\_world\_bss

通过对源文件的观察，我们可以推算出符号表中的一些内容，例如hello\_world\_data、hello\_world\_bss以及hello\_world是三个明显的在源文件中有定义的符号，一定会在符号表中有定义，分别对应的index是12、15和13。hello\_world\_data和hello\_world\_bss是数据，因此该符号的type是OBJECT，size是4个byte，hello\_world是function，因此它的type是FUNC，size是72个byte。Ndx定义了和该符号相关的section index，hello\_world这个符号是和.text section相关，index=1，hello\_world\_data位于.data section，因此index等于3。很奇怪，hello\_world\_bss的Ndx域并不是等于4（也就是.bss section），而是等于COM，COM是一个特别定义的section index，标识这是一个common block。要理解这一点需要一些背景知识：传统的unix编译器是允许在多个编译单元（c文件）中定义未初始化的全局变量的，也就是说，在两个c文件中都定义了名字一样的未初始化的全局变量是不会引起编译错误的，编译器在编译的时候会把未初始化的全局变量放入到common block中而不是.bss section。假如放入到.bss section，就意味着已经分配了该符号的地址，runtime的时候会占用内存。那么linker在合并.bss section的时候就会发现重复定义的符号了。gcc的编译器的缺省行为和传统unix c编译器一致，因此将hello\_world\_bss放入到common block中。其实这一点可能会给程序员（主要是粗心的程序员）带来非常难以解决的bug，你可以使用-fno-common来关闭这个特性，这时候，定义在多个文件中的同名的未初始化的全局变量在link的时候会报错。symbol value是一个和上下文相关的域，对于common block中的符号，该域说明了align属性。bind域说明了该符号的可见性和行为：GLOBAL表示可以对所有的.o文件可见，LOCAL表示对其他的.o文件不可见（对c程序员而言就是static修饰符，由于是local的，因此用static修饰的变量可以重名）。还有一个bind flag是WEAK，表示该符号是一个weak symbol。weak symbol的含义和global symbol含义是一样的，都是对外可见，只不过在如果有其他定义的同名的global symbol，那么weak symbol就消失鸟。

需要注意的是：LOCAL符号不是临时变量（hello\_world函数中的tmp），临时变量是放在stack中的，不会出现在符号表中。当然，也是所有定义在函数内部的变量都是临时变量，如果前面有static的修饰符，那么该变量虽然作用域是函数内部，但是也会出现在符号表中，只不过名字会是源程序中的符号附加一个“.xxxx”，xxxx是一个数字，大家可以自己编程序尝试一下。

结合这些flag和section index，我们可以一起探讨一下在符号同名的时候linker的行为（本来是应该在linker的章节描述的）：

（a）linker不允许有多个同名的GLOBAL符号出现

（b）同名的弱符号和global符号不会出错，选择global符号。同理，如果有一个global符号和多个在common block中的重名，那么linker会选取global符号。换句话说，linker认为未初始化的全局变量是weak symbol。

（c）同名的弱符号和common symbol（位于common block中），忽略weak symbol

（d）多个重名的common symbol，随便选择一个

下面我们看看hello\_world模块中引用的符号，看起来只有一个就是printf，对应index等于14的项次（由于gcc进行了优化，因此实际的符号名是puts）。对于这个符号，目前我们对其一无所知，因此其size等于0，type是NOTYPE，对应的section是UND，表示该符号undefine（在section table中，第一个entry就是undefine section）。

剩下的符号表中的item看起来都没有那么直观。index等于1的符号标识该object file对应的source code file的名字，ABS表示该符号已经尘埃落定，在后续的relocation中不会更改。type是SECTION的那些项次都是和section相关的符号定义，主要是用在relocation的时候。

最后需要解释的是那些带$的符号，这些符号是和ARM平台相关的，$a表示section 1（也就是正文段）这一坨代码是ARM code，如果是$t，那么说明这些code是Thumb code。$d表示0x3c开始的那一坨东东是数据（似乎没有讲清楚，别急，后面还会讲到的）。

内核中Elf32\_Sym和Elf64\_Sym这两个data struct反应了symbol table entry的数据结构。

5、Relocation information

在打开hello\_world.elf文件之前，你可以先自己凝视一下source code，猜测哪些符号需要relocation，然后再观察hello\_world.elf文件，验证自己的猜测。我们这里就不猜测了，直接看结果：

> Relocation section '.rel.text' at offset 0x498 contains 4 entries:   
> Offset Info Type Sym.Value Sym. Name   
> 00000010 00000e1c R\_ARM\_CALL 00000000 puts   
> 0000003c 00000602 R\_ARM\_ABS32 00000000 .rodata   
> 00000040 00000c02 R\_ARM\_ABS32 00000000 hello\_world\_data   
> 00000044 00000f02 R\_ARM\_ABS32 00000004 hello\_world\_bss

printf（puts）是一个未定义的符号，当然需要relocation的信息了。offset表示当需要relocation的时候，linker要修改的实际位置信息（相对于.text section的偏移）。实际的.text section dump如下：

> 00000000 :   
> 0: e92d4800 stmdb sp!, {fp, lr}   
> 4: e28db004 add fp, sp, #4 ; 0x4   
> 8: e24dd008 sub sp, sp, #8 ; 0x8   
> c: e59f0028 ldr r0, [pc, #40] ; 3c <.text+0x3c>   
> 10: ebfffffe bl 0    
> 14: e59f3024 ldr r3, [pc, #36] ; 40 <.text+0x40>   
> 18: e5932000 ldr r2, [r3]   
> 1c: e59f3020 ldr r3, [pc, #32] ; 44 <.text+0x44>   
> 20: e5933000 ldr r3, [r3]   
> 24: e0823003 add r3, r2, r3   
> 28: e50b3008 str r3, [fp, #-8]   
> 2c: e51b3008 ldr r3, [fp, #-8]   
> 30: e1a00003 mov r0, r3   
> 34: e24bd004 sub sp, fp, #4 ; 0x4   
> 38: e8bd8800 ldmia sp!, {fp, pc}   
> ...

在0x10的位置上，bl指令目前是跳转到0地址，当然，如果printf确定后，这里会修改可执行代码，让bl跳转到适当的位置去。R\_ARM\_CALL表示此处的relocation是和跳转指令BL或者BLX相关的。

剩余的三项是连续的，占据了正文段的最后。实际正文段的size是0x48，不过dump的时候只到0x38，后面的…就是全0的数据，分别表示常量字符串的指针、hello\_world\_data的地址以及hello\_world\_bss的地址。

内核中Elf32\_Rel（Elf32\_Rela）和Elf64\_Rel（Elf64\_Rela）这两个data struct反应了relocation entry的数据结构。Elf32\_Rela

6、平台信息

（1）编译器信息

.comment section中包含了编译器的信息，我们可以使用下面的命令来显示该section的信息：

> arm-linux-objdump -s –section .comment hello\_world.o > hello\_world.comment

结果如下：

> Contents of section .comment:   
> 0000 00474343 3a202843 6f646553 6f757263 .GCC: (CodeSourc   
> 0010 65727920 536f7572 63657279 20472b2b ery Sourcery G++   
> 0020 204c6974 65203230 30377131 2d323129 Lite 2007q1-21)   
> 0030 20342e32 2e302032 30303730 34313320 4.2.0 20070413   
> 0040 28707265 72656c65 61736529 00 (prerelease).

你使用的编译器的信息全部暴露了。.

（2）处理器信息

ARM.attributes包含了processor-specific的信息，具体如下：

> Attribute Section: aeabi   
> File Attributes   
> Tag\_CPU\_name: "ARM10TDMI"   
> Tag\_CPU\_arch: v5TE   
> Tag\_ARM\_ISA\_use: Yes   
> Tag\_ABI\_PCS\_wchar\_t: 4   
> Tag\_ABI\_FP\_denormal: Needed   
> Tag\_ABI\_FP\_exceptions: Needed   
> Tag\_ABI\_FP\_number\_model: IEEE 754   
> Tag\_ABI\_align8\_needed: Yes   
> Tag\_ABI\_align8\_preserved: Yes, except leaf SP   
> Tag\_ABI\_enum\_size: int   
> Tag\_ABI\_optimization\_goals: Aggressive Debug

更详细的解释请参考《ELF for ARM Architecture》文档。

（3）系统安全相关的section

.note.GNU-stack这个section和平台无关，不过也顺便在这里说一下。.note.GNU-stack是和系统安全相关的，我相信程序员都听说过buffer overflow attack，它是通过在栈上执行代码来攻击系统，一般而言，程序不需要在栈上执行代码，如果系统禁止了这个特性也就阻止了buffer overflow attack。因此，在编译的时候，如果程序不需要executable stack，那么就在.o文件中增加一个0字节的.note.GNU-stack section，以便告诉linker，该.o文件不需要executable stack，如果所有的.o文件都不需要executable stack，那么链接的结果，也就是可执行文件也不需要这个特性。在该程序被加载的时候，如果操作系统和底层硬件支持的话，那么该程序可以以non-executable stack的方式运行。

三、通过relocatable object file来深入理解c程序行为

relocatable object file的知识点很多，为了熟悉这些概念，本章将引入一个新的源文件goodbye\_world.c，并不断的修改它，然后可以用上一章的方法来观察这个源文件编译后的.o文件，并且在之前先猜一猜下面的几个问题的答案：

（1）这个goodbye\_world.o文件中和上一章的的hello\_world.o文件中的section有何不同？

（2）这个goodbye\_world.o文件中符号表有多少项？

（3）重定位信息包括多少项？

经过自己思考后，使用bin utilitis工具来观察实际的编译结果来验证自己的想法。

1、深入理解stack frame和函数调用。又一坨丑陋的代码横空出世啦，如下：

> #include    
> int goodbye\_world(int a0, int a1, int a2, int a3, int a4, int a5, int a6 )   
> {   
> int tmp0, tmp1, tmp2, tmp3, tmp4;
>
> tmp0 = a0;   
> tmp1 = a1;   
> tmp2 = a2;   
> tmp3 = a3;   
> tmp4 = a4;   
> tmp0 = tmp0 + tmp1 + tmp2 + tmp3 + tmp4 + a5 + a6;
>
> return tmp0;   
> }
>
> int byebye\_world( )   
> {   
> return goodbye\_world(1,2,3,4,5,6,7);   
> }

要理解后面这些反汇编代码，我们需要先看看《Procedure Call Standard for the ARM Architecture》（后面简称AAPCS）。我们来看看byebye\_world反汇编的结果：

> 00000090 :   
> 90: e92d4800 stmdb sp!, {fp, lr} －－－－－－将old fp和lr寄存器压入stack, sp=sp-8   
> 94: e28db004 add fp, sp, #4 ; 0x4 －－－－－设定fp，也就是stack frame pointer   
> 98: e24dd010 sub sp, sp, #16 ; 0x10 －－－－分配stack上的空间   
> 9c: e3a03005 mov r3, #5 ; 0x5 －－－－－－－将后三个参数保存在stack上   
> a0: e58d3000 str r3, [sp]   
> a4: e3a03006 mov r3, #6 ; 0x6   
> a8: e58d3004 str r3, [sp, #4]   
> ac: e3a03007 mov r3, #7 ; 0x7   
> b0: e58d3008 str r3, [sp, #8]   
> b4: e3a00001 mov r0, #1 ; 0x1 －－－－－前四个参数分别保存在了r0～r3寄存器中   
> b8: e3a01002 mov r1, #2 ; 0x2   
> bc: e3a02003 mov r2, #3 ; 0x3   
> c0: e3a03004 mov r3, #4 ; 0x4   
> c4: ebfffffe bl 0  －－－－－－调用点在这里   
> c8: e1a03000 mov r3, r0   
> cc: e1a00003 mov r0, r3   
> d0: e24bd004 sub sp, fp, #4 ; 0x4 －－－－－恢复上一个stack frame的stack pointer   
> d4: e8bd8800 ldmia sp!, {fp, pc}－－－－恢复上一个stack frame的stack frame pointer并返回

根据AAPCS，stack就是一段连续的内存，用来保存临时变量和参数传递。当然，一般而言，如果参数个数小于等于4个，那么使用r0～r3寄存器来传递参数就OK了，如果大于4个，那么需要通过stack来传递参数。byebye\_world的stack frame如下：

[![stackframe](/content/uploadfile/201502/a9daac3b4f2fa6bde77ef32d56ac5bdf20150209111342.gif "stackframe")](/content/uploadfile/201502/b7ede7c15975b187da3f6c8e5c47887020150209111215.gif)

从上面的图可以看出，一个函数的栈帧包括两个部分：一部分是保存寄存器的区域（上图中的绿色block，我们可以给它一个高大上的名字，Register Save Area，简称RSA），这个函数需要使用（也就是说将要被本函数修改）的寄存器都需要保存在这里，在退出函数的时候，要用这个区域的值来加载寄存器，以便恢复到调用该函数之前的现场。说到这里，你一定会置疑：为何程序中使用了r0 r1 r2和r3寄存器，没有保存在RSA区域呢？实际上这四个寄存器被用来作为传递参数寄存器以及临时寄存器（scratch register）的，因此不需要保存，如果需要使用其他的寄存器，都需要事先保存在栈上，以便函数返回之前恢复。以及另外一部分是保存临时变量和参数（参数个数>4个的那些），对应上图中蓝色的block。整个栈帧区域是需要8字节对齐的，因此上面有一个4字节的空洞。下面我们再看看goodbye\_world的反汇编：

> 00000000 :   
> 0: e52db004 str fp, [sp, #-4]! －－－－－－－保存old fp，sp=sp+4   
> 4: e28db000 add fp, sp, #0 ; 0x0 －－－－设定当前的frame pointer   
> 8: e24dd02c sub sp, sp, #44 ; 0x2c －－－－分配stack上的临时变量   
> ……   
> 88: e8bd0800 ldmia sp!, {fp} －－－－－－－－恢复fp   
> 8c: e12fff1e bx lr－－－－－－－－－－－－－返回函数调用处

这个函数的stack frame如下：

[![stackframe1](/content/uploadfile/201502/7ff09f613be8f61bfcc16a6174a413c120150209111551.gif "stackframe1")](/content/uploadfile/201502/6c90ef509043f7ab59e357e65d2ee6de20150209111447.gif)

和byebye\_world的stack frame不同的是，这里只保存了上一个stack frame的帧指针fp，为何不保存LR了呢？这主要是因为goodbye\_world是一个叶节点，该函数不会再调用其他的函数，因此LR寄存器是不会被修改的，因此在函数结尾可以直接跳转到LR寄存器的地址就OK了。此外，由于goodbye\_world使用了大量的local variable，因此它的stack frame比较大，你可以配合源代码推测出临时变量在stack frame上的位置。

对于gcc，其支持了几个操作stack frame的build-in函数（注意：是compiler build-in，不是c库中的函数），例如：

> void \* \_\_builtin\_return\_address (unsigned int level)   
> void \* \_\_builtin\_frame\_address (unsigned int level)

\_\_builtin\_frame\_address返回了指定level的frame pointer，level等于0返回当前栈帧的fp，level等于1返回的是调用者的frame pointer，以此类推。\_\_builtin\_return\_address类似，不过返回的是return address（也就是LR寄存器的内容）。stack frame pointer不是一个必须的地址指针，我们可以观察上面的汇编代码，虽然对临时变量的访问都是以 frame pointer作为基址寄存器的，不过，改成以stackpointer作为基址寄存器也是OK的，当然带来的坏处就是无法进行栈的回溯了。在goodbye\_world的执行过程中，stack pointer和frame pointer定义了goodbye\_world函数的stack frame的上限和下限，通过fp可以获取调用函数（caller，也就是byebye\_world）的stack frame，通过保存在栈上的old fp可以获取caller的frame pointer，根据这样的关系，不断的递推，可以获取整个函数调用链，也就完成了栈的回溯。所谓栈的回溯，也就是把一个大的memory region分成一个一个的stack frame。不过gcc也支持-fomi-frame-pointer这样的优化选项，这样的选项可以减少frame pointer的入栈，出栈，从而优化性能，带来的副作用就是在有些体系结构中无法进行debugging。

当然，也不是说编译的时候使用了-fomi-frame-pointer就一定不保存frame pointer，有的时候是不得不用，这时候可以完全体现frame pointer的价值。我们上文说过，对临时变量的访问可以以frame pointer作为基址寄存器的，也可以以stackpointer作为基址寄存器的，不过，当sp在runtime的时候会修改的时候，使用frame pointer作为基址寄存器访问临时变量会让编译器的日子好过一些，因为它不必跟踪stack pointer的变化了。例如：当程序中使用了alloca函数的时候，即便使用了-fomi-frame-pointer优化选项，调用alloca函数的那个函数栈帧仍然需要保存fp，并且用fp作为基地址访问临时变量。

2、理解static修饰符

在c程序中，static是一个存储修饰符（storage-class specifier），多用于描述全局变量或者函数，也可以用在函数中的变量定义。在函数中使用static比较少见，主要是为了保持住多次调用该函数的某些状态，使用要小心，可能会引入线程安全问题。下面我们先看看源代码：

> #include    
> extern int pp;
>
> static int \*gw\_si = &pp;－－－－－－－gw\_si的意思的goodbye world模块中的有赋初值的static数据   
> static int gw\_sui; －－－－－－－－－－这是未赋初值的static数据，ui就是uninitialize的意思
>
> static int goodbye\_world( )   
> {   
> int tmp;   
> static int gw\_si = 0x5678;   
> static int gw\_sui;
>
> printf("goodbye world!\n");   
> tmp = gw\_si + gw\_sui;
>
> return tmp;   
> }

我们主要是观察static的影响，对c程序员而言，static主要是用来封装，也就是说用static修饰的符号对其他模块都是不可见的，是本模块的私有数据。因此，模块中的gw\_si和gw\_sui都是其他模块不可见的符号。而在函数内定义的gw\_si和gw\_sui则仅仅是在函数内部有效，这四个符号编译器是如何处理的呢？

> 5: 00000000 4 OBJECT LOCAL DEFAULT 3 gw\_si   
> 7: 00000000 4 OBJECT LOCAL DEFAULT 5 gw\_sui.2142   
> 8: 00000004 4 OBJECT LOCAL DEFAULT 3 gw\_si.2141   
> 13: 00000004 4 OBJECT LOCAL DEFAULT 5 gw\_sui

已经初始化的static变量放到.data section，对应的section index等于3，gw\_si.2141是定义在函数中的那个符号，为了和全局变量区分开，函数中定义的gw\_si在符号表中并不是以它在source code中的符号定义出现，gcc给这个符号增加了一个数字，变成gw\_si.2141。对于未初始化的静态变量，我们可以和hello\_world中的变量进行比对。大家还记得hello\_world.c中的未初始化的全局变量的处理吗？它被放入到common block（很多人会认为应该放入.bss section）。虽然static的符号在源代码中没有初始化，不过根据c标准的定义，被static描述的对象需要在程序启动之前被初始化，指针类型的被初始化成NULL，int被初始化成0，这样的行为是和.bss section的行为类似的，因此gw\_sui和sw\_sui.2142都是放入到.bss section。当然，只要是static，那么该符号一定是LOCAL的，包括goodbye\_world这个用static声明的函数。

还有一个小小的知识点可以提一下就是这个.o文件中有了一个新的section，如下：

> [ 4] .rel.data REL 00000000 000524 000008 08 11 3 4

全局变量gw\_si被初始化成一个外部符号的地址，这时候，该地址还没有确定，因此这里需要一个重定位的信息。因此需要一个.rel.data的section来描述这个重定位的信息。

*原创文章，转发请注明出处。蜗窝科技*

[/basic_subject/compile-link-load.html](/basic_subject/compile-link-load.html)

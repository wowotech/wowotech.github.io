---
title: "ARM64的启动过程之（五）：UEFI"
date: 2015-10-30T19:27:58+08:00
url: "/armv8a_arch/UEFI.html"
gid: "227"
emlog_type: "blog"
summary: "在准备大刀阔斧进入start_kernel之际，我又重新review了一下head.S文件，看看是否有一些遗漏的知识点，很不幸，看到了 CONFIG_EFI这个配置项。当然，在一年前阅读kernel代码的时候就了解过相关的内容，但是，做为一个嵌入式工程师总是或多或少对其有些排斥， 因此习惯性的忽略掉CONFIG_EFI相关的代码，逃避总不是办法，在本文中，我们一起来探讨ARM64平台上UEFI相关"
author: "linuxer"
category: "ARMv8A Arch"
category_alias: "armv8a_arch"
tags: ["arm64", "UEFI"]
views: 53136
comment_count: 5
aliases:
  - "/armv8a_arch/227.html"
  - "/227.html"
---

一、前言

在准备大刀阔斧进入start\_kernel之际，我又重新review了一下head.S文件，看看是否有一些遗漏的知识点，很不幸，看到了CONFIG\_EFI这个配置项。当然，在一年前阅读kernel代码的时候就了解过相关的内容，但是，做为一个嵌入式工程师总是或多或少对其有些排斥，因此习惯性的忽略掉CONFIG\_EFI相关的代码，逃避总不是办法，在本文中，我们一起来探讨ARM64平台上UEFI相关的内容。

二、背景介绍

1、UEFI是什么鬼？

在个人电脑刚兴趣的时代，能够进入BIOS（Basic Input/Output System）解决一些计算机的问题绝对是高手中的高手（当年我就是这么骗到老婆的）。所谓BIOS实际上就是IBM PC兼容机（多么古老的一个词汇啊）主板上的固件（firmware），这些固件可以在系统启动过程中初始化硬件，self test，加载bootloader或者OS kernel，并且能为OS提供一些基础的服务。由于各种存在的问题，后来，Intel提出来EFI（Extensible Firmware Interface）来取代BIOS interface。2005年，Intel终止了EFI规范的开发，替代它的是Unified EFI Forum负责的UEFI（Unified Extensible Firmware Interface）specification。UEFI在系统中的位置如下（图片来自wiki）：

[![uefi](/content/uploadfile/201510/2242f3c37e46ef4c38b152f43d9ac33320151030112749.gif "uefi")](/content/uploadfile/201510/e1acc41f3cee9de326092ff1aa24a84c20151030112749.gif)

随着PC和服务器的飞速发展，软件和硬件厂商都不断的研发各种新的产品来应对客户的需求，在整合成系统的时候，有大量的协调的工作需要做，并且是越来越复杂。为了加快整合，降低设计复杂度，需要一个统一的接口标准，也就是传说中的UEFI了。有了UEFI，OS（软件厂商阵营）和固件（硬件厂商阵营）就有了接口规格，这样，大家可以各自进行开发，只要符合UEFI规格就OK了。如果硬件厂商有了创新性的硬件特性，如果不需要修改UEFI接口，那么系统还是可以无缝的衔接，如果需要修改接口，那么提前修改接口规格，让参与整个系统构建的厂商可以同步前进。同样的，从软件角度看，如果创新性的软件算法需要HW的支持，那么可以通过UEFI这样的接口和硬件厂商阵营进行交互，大大加快了将整个系统交付给客户的时间。

2、UEFI关ARM什么事？

如果ARM仅仅是将目光放在移动（嵌入式）市场，那么UEFI当然不关ARM什么事情。在嵌入式ARM平台上，ROM code ＋ bootloader（例如Uboot）＋ linux kernel这样的组合可以很好的工作。但是，在推出ARMv8以及64 bit架构的的处理器之后，ARM的野心已经不满足在移动市场上称王了。不过嵌入式平台和server或者PC类的平台是有区别的：嵌入式平台往往是高度定制化的平台，各个硬件模块都是不可分割的。如果你购买了一个手机，如果你觉得LCD不满意，是不可能单独去市场购买一个LCD屏更换的。而server（PC）类产品则不然，各个模块是可以更换的。例如：可以自由的去购买一个硬盘或者显卡进行更换。

在移动平台上，firmware（ROM code）怎么做是自己的事情，只要在应用层面提供一致性的接口就OK了，反正硬件以及OS不会更换。来到服务器平台，ARM必须和她的合作伙伴（SOC，外围硬件，OS厂商等等）一起面对这样的问题：

（1）硬件平台（firmware）和OS之间的接口如何定义？

（2）如何向OS传递硬件信息？

为了让各个厂商能够协同工作，尽快将ARM服务器推向市场，选择一个标准让大家follow是一个不错的主意。我们以OS提供商为例描述选择标准的好处。如果定义了硬件平台和OS之间的标准，OS提供商可以为ARMv8 server发布一个image而不会因为任何一点硬件平台的修改就得发布一个新的OS。因此，ARMv8 server选择UEFI是很自然的事情了。

3、UEFI如何定义系统的启动过程？

相信大家对传统的嵌入式ARM平台的启动过程都是有所了解的，系统reset后，各个ARM SOC的从ROM代码开始执行（一般ARM reset之后，PC＝0，而ROM缺省地址就是0）。根据SOC厂商约定的规则，ROM code会从外部设备（串口、网络、NAND flash、USB磁盘设备或者其他磁盘设备）加载linux bootloader，bootloader会收集硬件信息，之后加载linux kernel。在UEFI规范中定义了BOOT manager，它会根据保存在NVRAM参数来决定如何load EFI Application（可能是bootloader或者其他的image file）。EFI Application的格式必须符合PE（Portable Executable ）格式。PE是一种二进制可执行文件的格式（在linux世界中，我们多半熟悉的是ELF格式），由微软开发，广泛应用在Windows平台上。

在ARMv8平台上，firmware中的boot manager可以加载支持UEFI的传统的bootloader（例如uboot），然后由uboot加载kernel，这样，kernel其实不必关心什么UEFI。当然这样有些不直观，本来OS kernel关心的那些firmeare提供的各种信息都是由bootloader进行转接，严重影响了系统整合的效率（bootloader和kernel是由不同的团队开发），因此，linux kernel image自身也可以包装成一个EFI image，由boot manager直接加载，完成启动过程。

4、PE格式介绍

下面的图片是一个PE文件格式的示意图：

[![pe-file1](/content/uploadfile/201510/5b233a14259075519388720198b41b3820151030112754.gif "pe-file1")](/content/uploadfile/201510/0b7b5a396f9e2728331cca89c688f0c220151030112750.gif)

PE文件主要由两部分组成，一部分是为了兼容MS-DOS操作系统而包装的外壳（灰色block），主要由64B的MZ header和MS-DOS stub代码区组成。在遥远的MSDOS时代，其可执行文件就需要这样的一个header，MSDOS的program loader就会根据这个header加载程序运行。在Windows时代，微软提出了PE这种格式文件，它主要是运行在windows系列的操作系统中，但是，还需要考虑MSDSO的兼容性（也就是说当MSDOS执行PE格式的文件也能够提供足够的信息让用户知道如何处理）。MS-DOS stub block是一段stub code，这段区域的主要作用是：当PE格式的image在MS-DOS下加载运行的时候，程序会执行这个区域的代码（PE的代码都是for windows的，不可能在DOS下实际执行，因此，只能执行这些stub程序），当然运行的结果仅仅是打印“This program cannot be run in DOS mode”。

另外一个区域就是实际的PE格式的文件了。主要包括PE header（绿色block）、各种Section header（蓝色block，用于描述各个section）和各个section的实际的Data。各个域的具体含义我们会结合具体的代码在下一章描述。

三、代码分析：

1、MZ header。相关代码如下所示：

> #ifdef CONFIG\_EFI   
> efi\_head:   
> add x13, x18, #0x16 －－－－－－－－－－－－－－－－－－－－－－－－－－（2）   
> b stext   
> #else   
> b stext－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－（1）   
> .long 0   
> #endif   
> .quad \_kernel\_offset\_le－－－－－－－－－－－－－－－－－－－－－－－－－（3）   
> .quad \_kernel\_size\_le   
> .quad \_kernel\_flags\_le   
> .quad 0 // reserved   
> .quad 0 // reserved   
> .quad 0 // reserved   
> .byte 0x41－－－－－－－－－－－－Magic number, "ARM\x64"   
> .byte 0x52   
> .byte 0x4d   
> .byte 0x64
>
> #ifdef CONFIG\_EFI   
> .long pe\_header - efi\_head－－－－－－－－－－－－－－－－－－－－－－－（4）   
> #else   
> .word 0 // reserved   
> #endif

这里定义了64字节的kernel image header，应对两种场景：一种是从普通的linux bootloader加载内核，另外一种是从UEFI firmware直接加载kernel（定义了CONFIG\_EFI ），在这种场景下，这64B的内容被解释为MZ header。

（1）大部分的kernel image header都是相同的，除了第一个8-Byte和最后的4-Byte。没有定义CONFIG\_EFI 是大家都比较熟悉的场景，当bootloader完成kernel image的从外设到RAM的搬移之后会执行kernel image的第一条指令。因此，这里是一条跳转到stext的指令。

（2）如果想把自己伪装成一个UEFI image，kernel需要符合PE格式，下面是一个简化版本的PE格式的示意图（仅仅包括部分格式，主要用来说明兼容MS-DOS 相关部分的内容）：

[![pe file header](/content/uploadfile/201510/004daaf2ef9b207203e3e27252a1bbb820151030112756.gif "pe file header")](/content/uploadfile/201510/46c93364c68c86d081689dbb3371624020151030112755.gif)

上图中的灰色区域就是64-Byte的MZ header（对应kernel image header的内容），当然，对于linux kernel而言，它只是伪装成PE格式而已，只要能够提供足够的信息给UEFI firmware的boot manager就OK了。PE格式的文件除了包括一个MZ header，还包括一段MS-DOS stub（上图中的黄色区域），当然，对于linux kernel image，我们没有提供这部分的内容。这里“add x13, x18, #0x16”这条指令没有任何实际的意义，这条指令的opcode实际上就是MZ signature，用来标识这是一个DOS MZ executable的image。

（3）对于UEFI firmware而言，MS-DOS header大部分的区域都是没有什么用处的，因此正好可以用来提供信息，以便让linux的bootloader可以知道如何加载kernel（非UEFI加载的情况）。\_kernel\_offset\_le标识加载kernel的位置，如果等于0，表示加载到RAM的0地址的位置上。\_kernel\_size\_le表示需要加载的kernel image的长度，\_kernel\_flags\_le是表示kernel的一些属性，目前仅仅使用了bit 0，表示kernel的endianess。

（4）在UEFI firmware加载kernel的情况下，需要找到PE header以及各个section的定义了，以便boot manager完成加载kernel image的任务。在MS-DOS header中（offset是0x3c）有四个字节指向了PE header，通过它可以找到如何加载内核的各种信息。这个过程是这样的：UEFI firmware的boot manager如果发现了MZ header，那么就认为这是一个符合标准的EFI image，并在0x3c处获取PE header的位置，并继续解析其内容以便加载kernel image。

2、PE header相关代码

PE header包括三部分的内容：PE signature、COFF（Common Object File Format）file header和optional header。PE signature和COFF file header的代码如下：

> pe\_header:   
> .ascii "PE" －－－－－－－－－－－－－－－－PE header signanature   
> .short 0   
> coff\_header:   
> .short 0xaa64－－－－－－－－－－表示machine type是AArch64   
> .short 2－－－－－－－－－－－－该PE文件有多少个section   
> .long 0－－－－－－－－－－－－该文件的创建时间   
> .long 0－－－－－－－－－－－－符号表信息   
> .long 1－－－－－－－－－－－－符号表中的符号的数目   
> .short section\_table - optional\_header －－－－－－－－optional header的长度   
> .short 0x206－－－－－－－－－－－－－－－Characteristics，具体的含义请查看PE规格书

上节我们说过，通过MZ header可以找到PE header，所谓PE header的开始位置实际上就是一个“PE\0\0”的signature，随后紧接着就是COFF file header，COFF file header具体的定义如下（该表格来自PE specification）：

|  |  |  |  |
| --- | --- | --- | --- |
| **Offset** | **Size** | **Field** | **Description** |
| 0 | 2 | Machine | The number that identifies the type of target machine |
| 2 | 2 | NumberOfSections | The number of sections. This indicates the size of the section table, which immediately follows the headers. |
| 4 | 4 | TimeDateStamp | The low 32 bits of the number of seconds since 00:00 January 1, 1970 (a C run-time time\_t value), that indicates when the file was created. |
| 8 | 4 | PointerToSymbolTable | The file offset of the COFF symbol table, or zero if no COFF symbol table is present. This value should be zero for an image because COFF debugging information is deprecated. |
| 12 | 4 | NumberOfSymbols | The number of entries in the symbol table. This data can be used to locate the string table, which immediately follows the symbol table. This value should be zero for an image because COFF debugging information is deprecated. |
| 16 | 2 | SizeOfOptionalHeader | The size of the optional header, which is required for executable files but not for object files. This value should be zero for an object file. For a description of the header format, see section 3.4, “Optional Header (Image Only).” |
| 18 | 2 | Characteristics | The flags that indicate the attributes of the file |

NumberOfSections定义了PE文件中的section的数目，对于linux kernel image的PE文件，包括了两个section，一个是.reloc section（这是EFI application loader需要的，我们这里只是提供了一个dummy版本的.reloc section），另外一个是.text section（整个kernel image）。

通过COFF file header中的SizeOfOptionalHeader域，UEFI firmware可以知道optional header的size。之所以是“optional”主要是因为这些header内容不一定会存在。例如：对于object文件，这些header不存在。当然，我们是UEFI image file（可执行文件），因此这些optional header是必须提供的。optional\_header的最开始的域是optional header magic number，用来确定该PE文件是PE32还是PE32+格式的。根据UEFI规范，UEFI application file应该是PE32+格式的。PE32+格式的optional header格式如下：

|  |  |  |  |
| --- | --- | --- | --- |
| **Offset** | **Size** | **Header part** | **Description** |
| 0 | 28/24 | Standard fields | Fields that are defined for all implementations of COFF, including UNIX. |
| 28/24 | 68/88 | Windows-specific fields | Additional fields to support specific features of Windows (for example, subsystems). |
| 96/112 | Variable | Data directories | Address/size pairs for special tables that are found in the image file and are used by the operating system (for example, the import table and the export table). |

Standard fields包括了如何加载以及如何运行的信息。相关的代码如下：

> optional\_header:   
> .short 0x20b // PE32+ format   
> .byte 0x02 // MajorLinkerVersion   
> .byte 0x14 // MinorLinkerVersion   
> .long \_end - stext // SizeOfCode   
> .long 0 // SizeOfInitializedData   
> .long 0 // SizeOfUninitializedData   
> .long efi\_stub\_entry - efi\_head // AddressOfEntryPoint   
> .long stext\_offset // BaseOfCode

比较重要的信息包括：代码段在image file中的偏移（BaseOfCode），正文段的大小（SizeOfCode），data段的大小（SizeOfInitializedData），bss段的大小（SizeOfUninitializedData），加载到memory后入口函数（AddressOfEntryPoint，对于linux kernel而言，入口函数是efi\_stub\_entry）。

Windows-specific fields和Data directories主要被Windows操作系统的linker和loader使用的，这里就不详述了。

3、Section table和section Data

大家有兴趣可以自己查阅PE规格，我这里就偷懒啦，^\_^。

四、参考文献：

1、[https://lwn.net/Articles/584123/](https://lwn.net/Articles/584123/ "https://lwn.net/Articles/584123/")

2、[http://www.linaro.org/blog/when-will-uefi-and-acpi-be-ready-on-arm/](http://www.linaro.org/blog/when-will-uefi-and-acpi-be-ready-on-arm/ "http://www.linaro.org/blog/when-will-uefi-and-acpi-be-ready-on-arm/")

3、[https://lwn.net/Articles/574439/](https://lwn.net/Articles/574439/ "https://lwn.net/Articles/574439/")

4、PE规格书

5、UEFI规格书

*原创文章，转发请注明出处。蜗窝科技*

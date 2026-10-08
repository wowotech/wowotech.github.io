---
title: "X-007-UBOOT-DDR的初始化(Bubblegum-96平台)"
date: 2016-07-21T22:47:48+08:00
url: "/x_project/bubblegum_uboot_ddr.html"
gid: "319"
emlog_type: "blog"
summary: "\r\n\t到目前为止，“X \r\nProject”在Bubblegum-96平台上的代码，都是运行在SRAM中。由于SRAM的size很小（最多也就96KB），如果要做更多的事情，就必须把DDR跑起来。不过，关于Bubblegum-96平台的DDR \r\ndriver，我和codingbelief同学折腾了很久，试图找出一个最佳的方法，给大家呈现出DDR \r\ndriver的开发方法和开发步骤。最终，受限于"
author: "wowo"
category: "X Project"
category_alias: "x_project"
tags: ["SDRAM", "u-boot", "spl", "ddr"]
views: 12602
comment_count: 4
aliases:
  - "/x_project/319.html"
  - "/319.html"
---

#### 1. 前言

到目前为止，“[X Project](/forum/)”在Bubblegum-96平台上的代码，都是运行在SRAM中。由于SRAM的size很小（最多也就96KB），如果要做更多的事情，就必须把DDR跑起来。不过，关于Bubblegum-96平台的DDR driver，我和[codingbelief](/author/5)同学折腾了很久，试图找出一个最佳的方法，给大家呈现出DDR driver的开发方法和开发步骤。最终，受限于“资源”的短缺，还是失败了。

根据Bubblegum-96公开的资料，只知道它包含了一个2GB的、单bank的LPDDR，除此之外，找不到任何技术有关的细节，如LPDDR的datasheet、S900 DDR controller的说明、DDR时钟的配置等等。没有这些东西，我们根本无法完成DDR的配置，更不用说以此介绍、分析DDR driver了。

但是，虽然困难重重，“[X Project](/forum/)”还是要进行下去，既然常规方法走不通，我们就采用一些非常规的手段，无论如何，还是能把DDR成功的初始化起来的。由于是非常规手段，当然就无法开源，也无法给大家讲解了。

因此，本文关于DDR的技术细节不多，主要目的是结合DDR的初始化，进一步介绍嵌入式linux开发的基本过程，包括如下知识点：

> 嵌入式Linux的启动过程。
>
> u-boot SPL的使用场景。
>
> u-boot启动过程中DDR初始化的流程。

#### 2. Bubblegum-96的启动过程

由于RAM资源的短缺，嵌入式系统的启动过程是相当繁琐的，以Bubblegum-96为例：

> CPU启动时，只有96KB的SRAM可用。
>
> CPU启动时，ROM code只会从外部存储介质中（NAND、MMC、SD等）拷贝并执行2KB的代码。

首先与上面两个条件，Bubblegum-96的启动代码必须具备如下的特点。

1）软件从外部存储介质加载并执行的时候

> a）第一个被执行的image，必须小于2KB（我们暂时称它为SPL，Secondary Program Loader）。
>
> b）SPL在有限的size中，必须完成两个事情：初始化DDR；将后续的启动代码（如u-boot）从存储介质中copy到DDR中执行。
>
> c）u-boot在DDR中运行（不再受限于系统资源），进行必要的初始化之后，将linux kernel copy到DDR中并执行。
>
> d）linux kernel执行，并加载rootfs。

2）固件更新的时候（这里提供一种方案，将借助Android的fastboot，不唯一）

> a）第一个被执行的image（SPL），必须小于SRAM的size（根据经验，Bubblegum-96平台，要小于70KB）。
>
> b）通过ROM code的DFU程序，将SPL上传到SRAM并执行。
>
> c）SPL初始化DDR，并将控制权重新交给ROM code的DFU程序。
>
> d）通过ROM code的DFU程序，将u-boot（size不再受限）上传到DDR并执行。
>
> e）u-boot中启动fastboot服务，通过fastboot协议，更新固件。

本文将基于“[X Project](/sort/x_project)”前面的成果，介绍通过将SPL上传到SRAM并执行、初始化DDR，然后再把u-boot上传到DDR并执行的过程。

#### 3. 初始化过程介绍

##### 3.1 编写DDR driver，正确初始化DDR

由于非技术的原因，这里无法多说，感兴趣的同学，可以在资料充足的情况下，在自己的板子上尝试。最终的结果，就是导出一个类似于xxx\_ddr\_init()的接口，该接口会被SPL调用。

##### 3.2 在SPL的初始化代码中，调用DDR的init接口，初始化DDR，然后将控制权交回给ROM code

基于“[X-003-UBOOT-基于Bubblegum-96平台的u-boot移植说明](/x_project/bubblegum_uboot_porting.html)”的成果，我们已经可以在SPL的board\_init\_f接口中点亮一盏LED灯，现在要做的，就是调用DDR的初始化接口，如下：

> /\* [https://github.com/wowotechX/u-boot/blob/3e92a371cf72d47d95d0e31015eb685252901793/board/actions/bubblegum/board.c](https://github.com/wowotechX/u-boot/blob/3e92a371cf72d47d95d0e31015eb685252901793/board/actions/bubblegum/board.c "https://github.com/wowotechX/u-boot/blob/3e92a371cf72d47d95d0e31015eb685252901793/board/actions/bubblegum/board.c") \*/
>
> void board\_init\_f(ulong bootflag)   
> {   
> bubblegum\_early\_debug(1);
>
> #ifdef HAS\_DDR\_SOURCE\_CODE   
> s900\_ddr\_init();  
> #endif
>
> reboot\_to\_adfu();   
> }

注1：这里之所以要加一个宏定义，是因为源代码中没有DDR的source code，避免编译错误而已。

DDR初始化完成后，需要把控制权交回给ROM code的DFU程序，这可要费一番心思，如下：

> static void reboot\_to\_adfu(void)   
> {   
> void (\*call\_adfu)(void);
>
> //call\_adfu = (void (\*)(void))0xffff5a00;   
> call\_adfu = (void (\*)(void))0xffff0400;
>
> call\_adfu();   
> while (1);   
> }

我这里用了一个比较笨的方法，直接跳转到S900 ROM code的起始地址了，大家可以根据自己平台的实际情况，自行处理。

以上SPL并没有source code提供，我把编译出来的bin文件共享出来了，可参考：

> [https://github.com/wowotechX/tools/blob/73599ea17b517114bbf907ec002d6a3e6b475402/actions/splboot.bin](https://github.com/wowotechX/tools/blob/73599ea17b517114bbf907ec002d6a3e6b475402/actions/splboot.bin "https://github.com/wowotechX/tools/blob/73599ea17b517114bbf907ec002d6a3e6b475402/actions/splboot.bin")

##### 3.3 修改u-boot的代码，完善dram\_init接口，告诉u-boot当前DDR的size

该过程可基于“[X Project](/sort/x_project)”当前的u-boot代码：[https://github.com/wowotechX/u-boot](https://github.com/wowotechX/u-boot "https://github.com/wowotechX/u-boot")。主要改动如下：

> int dram\_init(void)   
> {   
> printf("dram\_init\n");
>
> bubblegum\_early\_debug(11);
>
> /\* no need do dram init in here, we have done it in SPL \*/
>
> gd->ram\_size = 2 \* 1024 \* 1024 \* 1024; /\* 2GB, TODO \*/
>
> printf("dram\_init OK\n");   
> return 0;   
> }

由于SPL已经完成了DDR初始化，这里什么事情都不需要做，只要通过gd->ram\_size告知u-boot DDR的size（这里是2GB）即可。当然，这里的赋值有点粗暴，后续再完善吧。

##### 3.4 修改u-boot的配置项，将u-boot编译到DDR中，从DDR执行

改动如下：

> /\* [https://github.com/wowotechX/u-boot/commit/3e92a371cf72d47d95d0e31015eb685252901793?diff=unified](https://github.com/wowotechX/u-boot/commit/3e92a371cf72d47d95d0e31015eb685252901793?diff=unified "https://github.com/wowotechX/u-boot/commit/3e92a371cf72d47d95d0e31015eb685252901793?diff=unified") \*/
>
> -#define CONFIG\_SYS\_TEXT\_BASE CONFIG\_SPL\_TEXT\_BASE   
> -#define CONFIG\_SYS\_INIT\_SP\_ADDR CONFIG\_SPL\_STACK   
> +#define CONFIG\_SYS\_TEXT\_BASE 0x11000000   
> +#define CONFIG\_SYS\_INIT\_SP\_ADDR (CONFIG\_SYS\_SDRAM\_BASE + 0x7ff00)   
>   
> /\* Some commands use this as the default load address, TODO \*/   
> -#define CONFIG\_SYS\_LOAD\_ADDR (CONFIG\_SYS\_SDRAM\_BASE)   
> +#define CONFIG\_SYS\_LOAD\_ADDR (CONFIG\_SYS\_SDRAM\_BASE + 0x7ffc0)

S900 DDR的地址映射是从0x0开始的，我们随便找一个地址（这里是0x11000000）。编译生成新的bin文件后，进行简单的测试，具体如下。

以上可参考如下patch：

> [https://github.com/wowotechX/u-boot/commit/3e92a371cf72d47d95d0e31015eb685252901793](https://github.com/wowotechX/u-boot/commit/3e92a371cf72d47d95d0e31015eb685252901793 "https://github.com/wowotechX/u-boot/commit/3e92a371cf72d47d95d0e31015eb685252901793")
>
> [https://github.com/wowotechX/tools/commit/73599ea17b517114bbf907ec002d6a3e6b475402](https://github.com/wowotechX/tools/commit/73599ea17b517114bbf907ec002d6a3e6b475402 "https://github.com/wowotechX/tools/commit/73599ea17b517114bbf907ec002d6a3e6b475402")

#### 4. 测试

在build目录编译完成后，按照如下的步骤执行：

1）按住Bubblegum-96的ADFU键，使板子进入DFU模式

2）按住Bubblegum-96的ADFU键不松开，将splboot.bin（就是我们的SPL image）上传到SRAM并执行

> sudo ../tools/dfu/dfu bubblegum 0xe406b200 ../tools/actions/splboot.bin 1

3）执行完毕后，会重新进入DFU模式，进入后，可以松开ADFU按键。

4）将u-boot上传到DDR并执行（注意上传位置和CONFIG\_SYS\_TEXT\_BASE 一致）

> sudo ../tools/dfu/dfu bubblegum 0x11000000 out/u-boot/u-boot-dtb.bin 1

5）检查串口打印，执行成功。

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/x_project/bubblegum_uboot_ddr.html)。

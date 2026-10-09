---
title: "X-005-UBOOT-device tree移植(Bubblegum-96平台)"
date: 2016-06-29T22:14:31+08:00
url: "/x_project/bubblegum_uboot_device_tree.html"
gid: "316"
emlog_type: "blog"
summary: "我们在“ X-004-UBOOT-串口驱动移植(Bubblegum-96平台) ”中，简单介绍了u-boot中serial driver的移植过程。由于serial driver是u-boot移植中的第一个driver，为了方便debug，并没有引入device tree。在serial driver ready之后，基本的console功能已经okay，基于此，我们可以着手增加device tr"
author: "wowo"
category: "X Project"
category_alias: "x_project"
tags: ["dts", "u-boot", "porting", "device_tree", "dtc", "dtb"]
views: 17953
comment_count: 8
aliases:
  - "/x_project/316.html"
  - "/316.html"
---

#### 1. 前言

我们在“[X-004-UBOOT-串口驱动移植(Bubblegum-96平台)](/x_project/bubblegum_uboot_serial.html)”中，简单介绍了u-boot中serial driver的移植过程。由于serial driver是u-boot移植中的第一个driver，为了方便debug，并没有引入device tree。在serial driver ready之后，基本的console功能已经okay，基于此，我们可以着手增加device tree功能。

很久以前，我们在博客上写了三篇device tree的分析文章（[Device Tree（一）：背景介绍](/device_model/why-dt.html)、[Device Tree（二）：基本概念](/device_model/dt_basic_concept.html)、[Device Tree（三）：代码分析](/device_model/dt-code-analysis.html)），这些文章的目的是介绍device tree背后的思想、原理、实现方法、等等，偏重于理论，相信给大家制造了不小的“心里压力”。

因此，本文将以“[X Project](/forum/)”为契机，从实践的角度，以使用者的视角，介绍device tree使用方法。相信通过本文，大家对device tree的理解会上一个新台阶，达到化繁为简、随心所欲的境地。

#### 2. 再谈device tree的思路和手段

相信大家初接触device tree的时候，一定有不知所措的感觉：天呐！怎么这么复杂？之所以得出这个结论，很大程度上是由那繁冗的xxx.dts文件，以及文件中那些奇奇怪怪的字符串所引起的。但从本质上，device tree要做的事情很简单：

> 就是把源代码中（不管是linux kernel或者u-boot）那些静态定义的struct device变量，替换为类似于自然语言的、人类可懂的、脚本性质的dts描述。
>
> 当然，为了适配设备模型，这些dts描述最终还是会转换为struct device变量。不过，大可放心，这个转换过程是由软件自动完成的，不需要驱动工程师操心。
>
> 最后，为了效率，软件不会直接解析dts描述（只有人才比较喜欢这种方式），而是解析由dts描述所生产的一个二进制文件（dtb）。dts转换为dtb，类似于C语言的编译过程，因此也不需要工程师操心。

因此，以我们的serial driver为例，device tree要做的事情，就是把：

> /\* [https://github.com/wowotechX/u-boot/blob/86bd15829d28b1bc0a8890ede5671c7d61f25d58/drivers/serial/serial\_owl.c](https://github.com/wowotechX/u-boot/blob/86bd15829d28b1bc0a8890ede5671c7d61f25d58/drivers/serial/serial_owl.c "https://github.com/wowotechX/u-boot/blob/86bd15829d28b1bc0a8890ede5671c7d61f25d58/drivers/serial/serial_owl.c") \*/   
> /\* TODO \*/   
> U\_BOOT\_DEVICE(owl\_serials) = {   
> .name = "serial\_owl",   
> };

替换为：

> /\* [https://github.com/wowotechX/u-boot/blob/5ce3bb6ea3b72f02647ad7cf6032c10a05cb9e21/arch/arm/dts/s900-bubblegum.dts](https://github.com/wowotechX/u-boot/blob/5ce3bb6ea3b72f02647ad7cf6032c10a05cb9e21/arch/arm/dts/s900-bubblegum.dts "https://github.com/wowotechX/u-boot/blob/5ce3bb6ea3b72f02647ad7cf6032c10a05cb9e21/arch/arm/dts/s900-bubblegum.dts") \*/
>
> uart5: serial@e012a000 {   
> compatible = "actions,s900-serial";   
> u-boot,dm-pre-reloc;   
> };

当然，dts文件需要转换为dtb，u-boot（或者linux kernel）启动之后，需要加载并分析dtb文件，最终再生成U\_BOOT\_DEVICE(xxx)。不过这样的逻辑是非常直白的，对一个软件工程师来说，就没有什么困难了。

注1：在device tree的本质功能之外，困扰大家最多的，就是dts文件中那些奇奇怪怪的符号，例如上面例子中的“compatible ”、“u-boot,dm-pre-reloc”、等等。这里有一个原则，掌握之后，一切都是纸老虎：所有的这些字段，在代码中都有对应的用处，一个grep指令，找到使用的地方，瞄一眼，就解决问题了。

#### 3. 移植过程

本章将以“Bubblegum-96平台”的serial driver为例，介绍u-boot中device tree的移植过程。

##### 3.1 在arch/arm/dts中添加一个空的DTS文件，并修改arch/arm/dts/Makefile，加入该文件

DTS文件的名称为s900-bubblegum.dts，当前只需要添加如下的内容（仅仅有一个根节点）：

> / {   
> };

修改后的Makefile文件为：

> diff --git a/arch/arm/dts/Makefile b/arch/arm/dts/Makefile
>
> index aa31fd9..d1226c2 100644
>
> --- a/arch/arm/dts/Makefile
>
> +++ b/arch/arm/dts/Makefile
>
> @@ -231,6 +231,9 @@ dtb-$(CONFIG\_SOC\_KEYSTONE) += k2hk-evm.dtb \
>
> k2e-evm.dtb \
>
> k2g-evm.dtb
>
> +dtb-$(CONFIG\_TARGET\_BUBBLEGUM) += \
>
> + s900-bubblegum.dtb
>
> +
>
> targets += $(dtb-y)

##### 3.2 配置u-boot，使能device tree有关的配置项

包括如下四个必须的配置项：

> CONFIG\_OF\_CONTROL
>
> CONFIG\_OF\_SEPARATE
>
> CONFIG\_FIT
>
> CONFIG\_DEFAULT\_DEVICE\_TREE

配置的过程为，cd ./xprj/build & make uboot-config

> Boot images --->   
> [ ] Support Flattened Image Tree
>
> Device Tree Control --->   
> [\*] Run-time configuration via Device Tree   
> Provider of DTB for DT control (Separate DTB for DT control) --->   
> (s900-bubblegum) Default Device Tree for DT control

其中CONFIG\_DEFAULT\_DEVICE\_TREE等于“s900-bubblegum”，需要和dts文件的名称（不包括后缀）相同。

##### 3.3 编译u-boot并解决出现的错误

执行cd ./xprj/build & make uboot后，出现编译错误：

> /home/pengo/work/xprj/u-boot/common/cli.c:200: undefined reference to `board\_run\_command'

因为我们没有定义CONFIG\_CMDLINE，当打开device tree有关的配置项，需要使用到board\_run\_command函数。没关系，先在board.c中伪造一个，如下：

> pengo@ubuntu:~/work/xprj/u-boot$ git diff board/actions/bubblegum/board.c   
> diff --git a/board/actions/bubblegum/board.c b/board/actions/bubblegum/board.c   
> index 4d58c18..5403ad0 100755   
> --- a/board/actions/bubblegum/board.c   
> +++ b/board/actions/bubblegum/board.c   
> @@ -112,3 +112,10 @@ int dram\_init(void)   
> bubblegum\_early\_debug(11);   
> return 0;   
> }   
> +   
> +int board\_run\_command(const char \*cmdline)   
> +{   
> + printf("## Commands are disabled. Please enable CONFIG\_CMDLINE.\n");   
> +   
> + return 1;   
> +}

再次编译，出现如下错误：

> tools/common/gcc-linaro-aarch64-linux-gnu-4.8-2013.12\_linux/bin/aarch64-linux-gnu-nm u-boot | grep \_\_rel\_dyn\_end | cut -f 1 -d ' '); tools/relocate-rela u-boot-nodtb.bin 0xe406b200 $start $end   
> /home/pengo/work/xprj/u-boot/scripts/dtc-version.sh: line 17: dtc: command not found   
> /home/pengo/work/xprj/u-boot/scripts/dtc-version.sh: line 18: dtc: command not found

呵呵呵，没有dtc，不过已经开始编译我们新增的dts文件了，算是好消息。出错不要紧，下载并编译dtc就行了（机器上正确安装dtc的同学可以忽略此步骤）：

> sudo apt-get remove device-tree-compiler   
> sudo apt-get install flex   
> sudo apt-get install bison
>
> git clone https://kernel.org/pub/scm/utils/dtc/dtc.git -b 1.4.1
>
> `c`d dtc   
> make   
> make install
>
> `export PATH=$HOME/bin/:$PATH`
>
> `注1：默认情况下，d`tc被安装到~/bin下面了，所以需要把~/bin目录添加到PATH环境变量中。也可以安装到其它位置，或者把上面的命令写到当前用户的profile文件中（一般的linux系统默认已经有了，具体可参考~/.profile文件）。

再次编译，还是报错：

> Error: /home/pengo/work/xprj/u-boot/arch/arm/dts/s900-bubblegum.dts:7.1-2 syntax error

我们的DTS文件是一个空文件，竟然还有语法错误？经过尝试，必须要在dts的开头加入：

> /dts-v1/;
>
> 注2：关于dts-v1的意义，可参考dtc的source code（任何疑惑，我们都可以从代码中找到答案，这一点很重要！），这里不再分析了。

再次编译，okay了，生成如下文件：

> pengo@ubuntu:~/work/xprj/build$ ls out/u-boot/u-boot\* -l   
> -rwxr-xr-x 1 pengo pengo 990170 2016-06-28 02:01 out/u-boot/u-boot   
> -rw-r--r-- 1 pengo pengo 67928 2016-06-28 02:01 out/u-boot/u-boot.bin   
> -rw-r--r-- 1 pengo pengo 12217 2016-06-11 20:37 out/u-boot/u-boot.cfg   
> -rw-r--r-- 1 pengo pengo 72 2016-06-28 02:01 out/u-boot/u-boot.dtb  
> -rw-r--r-- 1 pengo pengo 67928 2016-06-28 02:01 out/u-boot/u-boot-dtb.bin  
> -rw-r--r-- 1 pengo pengo 1304 2016-06-11 20:37 out/u-boot/u-boot.lds   
> -rw-r--r-- 1 pengo pengo 119958 2016-06-28 02:01 out/u-boot/u-boot.map   
> -rw-r--r-- 1 pengo pengo 67856 2016-06-28 02:01 out/u-boot/u-boot-nodtb.bin  
> -rw-r--r-- 1 pengo pengo 203666 2016-06-28 02:01 out/u-boot/u-boot.srec   
> -rw-r--r-- 1 pengo pengo 37792 2016-06-28 02:01 out/u-boot/u-boot.sym

其中out/u-boot/u-boot.dtb是单独编出来的dtb文件，可以通过dtc命令反编译，查看对应的dts：

> pengo@ubuntu:~/work/xprj/build$ dtc -I dtb -O dts out/u-boot/u-boot.dtb
>
> /dts-v1/;   
> / {   
> };

而out/u-boot/u-boot-dtb.bin，是携带了dtb信息的bin文件，上传到板子中运行，看看什么效果：

> sudo ../tools/dfu/dfu bubblegum 0xe406b200 out/u-boot/u-boot-dtb.bin 1

检查串口打印，没有看到任何DTS的信息？通过阅读source code，发现fdtdec\_prepare\_fdt有一些debug信息，不过是由DEBUG控制，修改版型的头文件，把DEBUG选项打开：

> diff --git a/include/configs/bubblegum.h b/include/configs/bubblegum.h   
> index 1698266..28058fc 100644   
> --- a/include/configs/bubblegum.h   
> +++ b/include/configs/bubblegum.h   
> @@ -10,6 +10,8 @@   
> #ifndef \_\_BUBBLEGUM\_H   
> #define \_\_BUBBLEGUM\_H   
> +#define DEBUG   
> +

再次编译，运行。多出来好多打印，还是没有dts相关的，怪异。接着看代码：

> fdtdec\_setup   
> fdtdec\_prepare\_fdt

原来只有异常时才有打印，没有消息就是好消息，进行下一步，在serial driver支持device tree功能。

##### 3.4 修改serial driver，增加对device tree的支持

为了简单，这里仅仅将serial driver中的U\_BOOT\_DEVICE宏定义，替换为dts文件中的节点，其它较为复杂、严谨的逻辑，后面再说。

1）在dts中添加一个serial的节点。

> pengo@ubuntu:~/work/xprj/u-boot$ git diff arch/arm/dts/s900-bubblegum.dts   
> diff --git a/arch/arm/dts/s900-bubblegum.dts b/arch/arm/dts/s900-bubblegum.dts   
> index 7c1368e..f8fbf54 100644   
> --- a/arch/arm/dts/s900-bubblegum.dts   
> +++ b/arch/arm/dts/s900-bubblegum.dts   
> @@ -6,4 +6,7 @@   
> /dts-v1/;   
> / {   
> + uart5: serial@e012a000 {   
> + compatible = "actions,s900-serial";   
> + };  
> };

2）将“drivers/serial/serial\_owl.c”有关U\_BOOT\_DEVICE的定义删掉，并按照dts中“compatible”字段的定义，增加match table，如下：

> pengo@ubuntu:~/work/xprj/u-boot$ git diff drivers/serial/serial\_owl.c   
> diff --git a/drivers/serial/serial\_owl.c b/drivers/serial/serial\_owl.c   
> index b7e8c3d..3303b3b 100644   
> --- a/drivers/serial/serial\_owl.c   
> +++ b/drivers/serial/serial\_owl.c   
> @@ -168,15 +168,16 @@ static const struct dm\_serial\_ops owl\_serial\_ops = {   
> .setbrg = owl\_serial\_setbrg,   
> };   
>   
> +static const struct udevice\_id owl\_serial\_ids[] = {   
> + { .compatible = "actions,s900-serial", },   
> + { }   
> +};   
> +
>
> U\_BOOT\_DRIVER(serial\_owl) = {   
> .name = "serial\_owl",   
> .id = UCLASS\_SERIAL,   
> + .of\_match = owl\_serial\_ids,  
> .probe = owl\_serial\_probe,   
> .ops = &owl\_serial\_ops,   
> .flags = DM\_FLAG\_PRE\_RELOC,   
> };   
> -   
> -/\* TODO \*/   
> -U\_BOOT\_DEVICE(stm32\_serials) = {   
> - .name = "serial\_owl",   
> -};

3）编译，运行，串口输出应该正常才是。

好吧，失败了，检查原因吧。这时LED debug的方法可以派上用场了（具体可参考“[通过点亮LED的方法调试嵌入式代码](/soft/debug_using_led.html)”），不过从现状看，只有LED0亮，说明board\_early\_init\_f已经执行，但owl\_serial\_probe没有执行。

在修改代码debug之前，先看看代码逻辑吧：怀疑initf\_dm？是serial\_init？先从initf\_dm看起：

> initf\_dm   
> dm\_init\_and\_scan   
> dm\_scan\_fdt   
> dm\_scan\_fdt\_node

中有这样一句话：

> int dm\_scan\_fdt\_node(struct udevice \*parent, const void \*blob, int offset,   
> bool pre\_reloc\_only)   
> {   
> int ret = 0, err;
>
> for (offset = fdt\_first\_subnode(blob, offset);   
> offset > 0;   
> offset = fdt\_next\_subnode(blob, offset)) {   
> if (pre\_reloc\_only &&   
> !fdt\_getprop(blob, offset, "u-boot,dm-pre-reloc", NULL))  
> continue;   
> …   
> }
>
> if (ret)   
> dm\_warn("Some drivers failed to bind\n");
>
> return ret;   
> }

由于调用过程中，pre\_reloc\_only为true，则需要检查u-boot,dm-pre-reloc字段，而我们的“serial@e012a000 ”节点中，并没有该字段，相当于找不到。加入试试，如下：

> /\* [https://github.com/wowotechX/u-boot/blob/5ce3bb6ea3b72f02647ad7cf6032c10a05cb9e21/arch/arm/dts/s900-bubblegum.dts](https://github.com/wowotechX/u-boot/blob/5ce3bb6ea3b72f02647ad7cf6032c10a05cb9e21/arch/arm/dts/s900-bubblegum.dts "https://github.com/wowotechX/u-boot/blob/5ce3bb6ea3b72f02647ad7cf6032c10a05cb9e21/arch/arm/dts/s900-bubblegum.dts") \*/
>
> uart5: serial@e012a000 {   
> compatible = "actions,s900-serial";   
> u-boot,dm-pre-reloc;  
> };

再次编译、运行，正常的串口打印又出来了，说明我们成了。

注3：以上内容，可参考如下的patch，[https://github.com/wowotechX/u-boot/commit/5ce3bb6ea3b72f02647ad7cf6032c10a05cb9e21](https://github.com/wowotechX/u-boot/commit/5ce3bb6ea3b72f02647ad7cf6032c10a05cb9e21 "https://github.com/wowotechX/u-boot/commit/5ce3bb6ea3b72f02647ad7cf6032c10a05cb9e21")。

#### 4. 总结

本文比较简单，以简单的serial driver为例，提供了一个关于怎么使用device tree思路。例子中的dts文件，只有“compatible ”和“u-boot,dm-pre-reloc”两个属性值，实际的开发过程中，肯定不会这么简单，但我想告诉大家的是：

> 不要被复杂的device tree吓到，不要被庞大的dts文件吓到，从本质出发，理解DTS的工作原理后，dts文件中任何奇奇怪怪的属性，都可以在source code中找到使用场景，进而很容易的理解之。

因此，我可以很自信的在文章结尾宣布：如果大家理解了本文所要表达内容之后，device tree就不再由任何的困难和神秘感了。

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/x_project/bubblegum_uboot_device_tree.html)。

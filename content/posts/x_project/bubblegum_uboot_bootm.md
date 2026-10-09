---
title: "X-011-UBOOT-使用bootm命令启动kernel(Bubblegum-96平台)"
date: 2016-09-09T22:18:12+08:00
url: "/x_project/bubblegum_uboot_bootm.html"
gid: "334"
emlog_type: "blog"
summary: "我们在“ X-010-UBOOT-使用booti命令启动kernel(Bubblegum-96平台) ”中介绍了使用u-boot booti指令加载并运行ARM64 Image格式kernel的方法。与此同时，我们在“ u-boot FIT image介绍 ”介绍了一种新的uImage（u-boot Image）格式----FIT uImage。本文将基于这两篇文章，介绍FIT uImage的编译"
author: "wowo"
category: "X Project"
category_alias: "x_project"
tags: ["arm64", "u-boot", "uboot", "bootm", "fit", "uImage", "its", "itb"]
views: 17272
comment_count: 8
aliases:
  - "/x_project/334.html"
  - "/334.html"
---

#### 1. 前言

我们在“[X-010-UBOOT-使用booti命令启动kernel(Bubblegum-96平台)](/x_project/bubblegum_uboot_booti.html)”中介绍了使用u-boot booti指令加载并运行ARM64 Image格式kernel的方法。与此同时，我们在“[u-boot FIT image介绍](/u-boot/fit_image_overview.html)”介绍了一种新的uImage（u-boot Image）格式----FIT uImage。本文将基于这两篇文章，介绍FIT uImage的编译、启动等方法，目的有二：

> 1）作为“[u-boot FIT image介绍](/u-boot/fit_image_overview.html)”的实践篇。
>
> 2）以后“[X Project](/forum/)”和u-boot有关的image格式，将统一使用FIT uImage。

#### 2. FIT uImage的生成

##### 2.1 向unify kernel的目标迈进

“[u-boot FIT image介绍](/u-boot/fit_image_overview.html)”中提到了，为了实现unify kernel的目标，需要为不同的平台编译同一个kernel image。换句话说，就是要有相同的kernel defconfig文件。因此，以Bubblegum-96平台为例，我们要建立统一的defconfig文件----xprj\_defconfig，步骤如下：

> cd ./linux   
> make ARCH=arm64 allnoconfig   
> # 直接保存并退出   
> cp .config arch/arm64/configs/xprj\_defconfig
>
> # 生成的deconfig文件可参考   
> [# https://github.com/wowotechX/linux/commit/1d9204207e91ffc21b845552db5756512274a37d](https://github.com/wowotechX/linux/commit/1d9204207e91ffc21b845552db5756512274a37d)

注1：记得我们在“[X-010-UBOOT-使用booti命令启动kernel(Bubblegum-96平台)](/x_project/bubblegum_uboot_booti.html)”中，为了删减kernel默认的配置项，累的死去活来的，其实有简便方法----make allnoconfig，会生成指定平台下能work的最小kernel。

与此同时，修改“[X Project](/forum/)”的编译脚本，ARM64架构的版型，统一使用xprj\_defconfig，如下：

> diff --git a/Makefile b/Makefile   
> index b51d943..bd25f83 100644   
> --- a/Makefile   
> +++ b/Makefile   
> @@ -22,6 +22,10 @@ OUT\_DIR=$(BUILD\_DIR)/out   
> UBOOT\_OUT\_DIR=$(OUT\_DIR)/u-boot   
> KERNEL\_OUT\_DIR=$(OUT\_DIR)/linux
>
> +ifeq ($(BOARD\_ARCH), arm64)   
> +KERNEL\_DEFCONFIG=xprj\_defconfig   
> +endif   
> +  
> all: uboot kernel
>
> clean: dfu-clean uboot-clean kernel-clean
>
> @@ -59,13 +63,13 @@ uboot-clean:   
> #   
> kernel-config:   
> mkdir -p $(KERNEL\_OUT\_DIR)   
> - cp -f $(KERNEL\_DIR)/arch/$(BOARD\_ARCH)/configs/$(BOARD\_NAME)\_defconfig $(KERNEL\_OUT\_DIR)/.config   
> + cp -f $(KERNEL\_DIR)/arch/$(BOARD\_ARCH)/configs/$(KERNEL\_DEFCONFIG) $(KERNEL\_OUT\_DIR)/.config  
> make -C $(KERNEL\_DIR) KBUILD\_OUTPUT=$(KERNEL\_OUT\_DIR) ARCH=$(BOARD\_ARCH) menuconfig   
> - cp -f $(KERNEL\_OUT\_DIR)/.config $(KERNEL\_DIR)/arch/$(BOARD\_ARCH)/configs/$(BOARD\_NAME)\_defconfig   
> + cp -f $(KERNEL\_OUT\_DIR)/.config $(KERNEL\_DIR)/arch/$(BOARD\_ARCH)/configs/$(KERNEL\_DEFCONFIG)
>
> kernel:   
> mkdir -p $(KERNEL\_OUT\_DIR)   
> - make -C $(KERNEL\_DIR) CROSS\_COMPILE=$(CROSS\_COMPILE) KBUILD\_OUTPUT=$(KERNEL\_OUT\_DIR) ARCH=$(BOARD\_ARCH) $(BOARD\_NAME)\_defconfig   
> + make -C $(KERNEL\_DIR) CROSS\_COMPILE=$(CROSS\_COMPILE) KBUILD\_OUTPUT=$(KERNEL\_OUT\_DIR) ARCH=$(BOARD\_ARCH) $(KERNEL\_DEFCONFIG)  
> make -C $(KERNEL\_DIR) CROSS\_COMPILE=$(CROSS\_COMPILE) KBUILD\_OUTPUT=$(KERNEL\_OUT\_DIR) ARCH=$(BOARD\_ARCH) Image dtbs
>
> kernel-clean:

具体可参考“<https://github.com/wowotechX/build/commit/bba23bf1d63aabb797400185e4d6d764b651e3b6>”。

##### 2.2 基于新生成的kernel config，打开对bubblegum的支持（为了编译dtb文件）

> CONFIG\_ARCH\_OWL=y

具体可参考“[X-010-UBOOT-使用booti命令启动kernel(Bubblegum-96平台)](/x_project/bubblegum_uboot_booti.html)”中有关的描述，patch文件如下：

<https://github.com/wowotechX/linux/commit/9a4169ba5187d748a99c11d524bcd1238fd92408>

##### 2.3 增加.its文件

参考u-boot的例子，新建一个.its文件，名称为fit\_uImage.its，如下：

> cd ./build
>
> cp ../u-boot/doc/uImage.FIT/kernel\_fdt.its fit\_uImage.its

根据x project的实际情况，修改its文件，增加Kernel image和dtb文件两个节点，如下（注意，这个its文件是有问题的，后面调试的时候再改）：

<https://github.com/wowotechX/build/blob/b71ccd4c7530ec6c5aed7bab0cbd74f48f1fe48e/fit_uImage.its>

与此同时，修改编译脚本，加入uImage的编译命令（make uImage），借助u-boot/tools目录下的mkimage工具，编译uImage：

> +UIMAGE\_ITS\_FILE=$(BUILD\_DIR)/fit\_uImage.its   
> +UIMAGE\_ITB\_FILE=$(OUT\_DIR)/xprj\_uImage.itb   
> …   
> +uImage:   
> + mkdir -p $(OUT\_DIR)   
> + $(UBOOT\_OUT\_DIR)/tools/mkimage -f $(UIMAGE\_ITS\_FILE) $(UIMAGE\_ITB\_FILE)

其中fit\_uImage.its位于当前build目录；xprj\_uImage.itb是将要生成的FIT uImage文件，位于./build/out目录；mkimage工具位于u-boot/tools目录，编译u-boot之后会自定生成。

##### 2.4 编译生成FIT uImage

在build目录执行make kernel，生成kernel image和对应的dtb文件之后，再执行make uImage，即可将它们打包成FIT uImage。然后我们可以使用mkimage查看新生成的uImage的信息，如下：

> pengo@ubuntu:~/work/xprj/build$ ./out/u-boot/tools/mkimage -l out/xprj\_uImage.itb   
> FIT description: U-Boot uImage source file for X project   
> Created: Sat Sep 3 00:05:17 2016   
> Image 0 ([kernel@arm64](mailto:kernel@arm64))   
> Description: Unify(TODO) ARM64 Linux kernel   
> Created: Sat Sep 3 00:05:17 2016   
> Type: Kernel Image   
> Compression: uncompressed   
> Data Size: 1229056 Bytes = 1200.25 kB = 1.17 MB   
> Architecture: ARM   
> OS: Linux   
> Load Address: 0x00080000   
> Entry Point: 0x00080000   
> Hash algo: crc32   
> Hash value: ff814746   
> Hash algo: sha1   
> Hash value: db4b1b6f40827d88b2e754e795c432cddf41f9bf   
> Image 1 ([fdt@bubblegum96](mailto:fdt@bubblegum96))  
> Description: Flattened Device Tree blob for Bubblegum-96   
> Created: Sat Sep 3 00:05:17 2016   
> Type: Flat Device Tree   
> Compression: uncompressed   
> Data Size: 181 Bytes = 0.18 kB = 0.00 MB   
> Architecture: ARM   
> Hash algo: crc32   
> Hash value: 8ee556df   
> Hash algo: sha1   
> Hash value: fd590fa50b2f79c18c736cfb410da70feadbfdaa   
> Default Configuration: ['conf@bubblegum96'](mailto:'conf@bubblegum96')  
> Configuration 0 ([conf@bubblegum96](mailto:conf@bubblegum96))  
> Description: Boot Linux kernel with FDT blob   
> Kernel: [kernel@arm64](mailto:kernel@arm64)  
> FDT: fdt@bubblegum96

Image信息和fit\_uImage.its中所描述的完全一致，说明如下：

> 包含两个Image：   
> Image0，名称为[kernel@arm64](mailto:kernel@arm64)，类型是“Kernel Image”，Architecture为“ARM”，没有压缩，Load和Entry都是“0x00080000”；   
> Image1，名称为[fdt@bubblegum96](mailto:fdt@bubblegum96)，类型是“Flat Device Tree”，Architecture为“ARM”，没有压缩，Load和Entry未指定。
>
> 包含一个Configuration，名称为[conf@bubblegum96](mailto:conf@bubblegum96)，该Configuration共包括“[kernel@arm64](mailto:kernel@arm64)”和“[fdt@bubblegum96](mailto:fdt@bubblegum96)”两个Image。
>
> 默认的Configuration就是[conf@bubblegum96](mailto:conf@bubblegum96)。

#### 3. FIT uImage的启动

##### 3.1 使用bootm启动FIT uImage

生成“xprj\_uImage.itb”之后，我们可以使用DFU工具将它下载到板子的DDR中，并使用bootm命令启动它（有关bootm命令的支持，可参考“[X-010-UBOOT-使用booti命令启动kernel(Bubblegum-96平台)](/x_project/bubblegum_uboot_booti.html)”），如下[1]：

> # 执行spl image，初始化DDR   
> sudo ../tools/dfu/dfu bubblegum 0xe406b200 ../tools/actions/splboot.bin 1
>
> # 将xprj\_uImage.itb下载到DDR的收地址（最后一个参数表示不执行）   
> sudo ../tools/dfu/dfu bubblegum 0x0 ./out/xprj\_uImage.itb 0
>
> #下载并执行u-boot   
> sudo ../tools/dfu/dfu bubblegum 0x11000000 out/u-boot/u-boot-dtb.bin 1

启动到u-boot命令行执行，以xprj\_uImage.itb所在的地址为参数，执行bootm命令，不幸的失败了，错误信息如下：

> [xprj]# bootm 0x0   
> ## Current stack ends at 0x3ffc14e0 \* kernel: cmdline image address = 0x00000000   
> ## Loading kernel from FIT Image at 00000000 ...   
> No configuration specified, trying default...   
> Found default configuration: 'conf@bubblegum96'   
> Using 'conf@bubblegum96' configuration   
> Trying 'kernel@arm64' kernel subimage   
> Description: Unify(TODO) ARM64 Linux kernel   
> Type: Kernel Image   
> Compression: uncompressed   
> Data Start: 0x000000ec   
> Data Size: 1229056 Bytes = 1.2 MiB   
> Architecture: ARM   
> OS: Linux   
> Load Address: 0x00080000   
> Entry Point: 0x00080000   
> Hash node: 'hash@1'   
> Hash algo: crc32   
> Hash value: ff814746   
> Hash len: 4   
> Hash node: 'hash@2'   
> Hash algo: sha1   
> Hash value: db4b1b6f40827d88b2e754e795c432cddf41f9bf   
> Hash len: 20   
> Verifying Hash Integrity ... crc32 error!   
> Bad hash value for 'hash@1' hash node in 'kernel@arm64' image node   
> Bad Data Hash   
> ERROR: can't get kernel image!   
> Command failed, result=1

##### 3.2 删掉.its文件中的hash节点

原来hash值错了，好像fit\_uImage.its指定了hash节点，但是我们没有特意的为两个Image计算hash值，简单起见，先删掉吧，如下：

> kernel@arm64 {   
> description = "Unify(TODO) ARM64 Linux kernel";   
> data = /incbin/("./out/linux/arch/arm64/boot/Image");   
> type = "kernel";   
> arch = "arm";   
> os = "linux";   
> compression = "none";   
> load = <0x00080000>;   
> entry = <0x00080000>;   
> };   
> fdt@bubblegum96 {   
> description = "Flattened Device Tree blob for Bubblegum-96";   
> data = /incbin/("./out/linux/arch/arm64/boot/dts/actions/s900-bubblegum.dtb");   
> type = "flat\_dt";   
> arch = "arm";   
> compression = "none";   
> };

重复3.1的步骤，再来一次，还有问题：

> xprj]# bootm 0x0   
> ## Current stack ends at 0x3ffc14e0 \* kernel: cmdline image address = 0x00000000   
> ## Loading kernel from FIT Image at 00000000 ...   
> No configuration specified, trying default...   
> Found default configuration: ['conf@bubblegum96'](mailto:'conf@bubblegum96')  
> Using 'conf@bubblegum96' configuration   
> Trying 'kernel@arm64' kernel subimage   
> Description: Unify(TODO) ARM64 Linux kernel   
> Type: Kernel Image   
> Compression: uncompressed   
> Data Start: 0x000000ec   
> Data Size: 1229056 Bytes = 1.2 MiB   
> Architecture: ARM   
> OS: Linux   
> Load Address: 0x00080000   
> Entry Point: 0x00080000   
> Verifying Hash Integrity ... OK   
> Unsupported Architecture  
> ERROR: can't get kernel image!   
> Command failed, result=1

##### 3.3 将架构修改为“arm64”

“Unsupported Architecture”，不支持的架构？在u-boot的source code中，查找一下架构有关的代码，原来要把arch改为arm64，如下：

> kernel@arm64 {   
> description = "Unify(TODO) ARM64 Linux kernel";   
> data = /incbin/("./out/linux/arch/arm64/boot/Image");   
> type = "kernel";   
> arch = "arm64";   
> os = "linux";   
> compression = "none";   
> load = <0x00080000>;   
> entry = <0x00080000>;   
> };   
> fdt@bubblegum96 {   
> description = "Flattened Device Tree blob for Bubblegum-96";   
> data = /incbin/("./out/linux/arch/arm64/boot/dts/actions/s900-bubblegum.dtb");   
> type = "flat\_dt";   
> arch = "arm64";   
> compression = "none";   
> };

重复3.1的步骤，还有问题：

> [xprj]# bootm 0x0   
> ## Current stack ends at 0x3ffc14e0 \* kernel: cmdline image address = 0x00000000   
> ## Loading kernel from FIT Image at 00000000 ...   
> No configuration specified, trying default...   
> Found default configuration: ['conf@bubblegum96'](mailto:'conf@bubblegum96')  
> Using 'conf@bubblegum96' configuration   
> Trying 'kernel@arm64' kernel subimage   
> Description: Unify(TODO) ARM64 Linux kernel   
> Type: Kernel Image   
> Compression: uncompressed   
> Data Start: 0x000000ec   
> Data Size: 1229056 Bytes = 1.2 MiB   
> Architecture: AArch64   
> OS: Linux   
> Load Address: 0x00080000   
> Entry Point: 0x00080000   
> Verifying Hash Integrity ... OK   
> kernel data at 0x000000ec, len = 0x0012c100 (1229056)   
> \* ramdisk: using config 'conf@bubblegum96' from image at 0x00000000   
> \* ramdisk: no 'ramdisk' in config   
> Loading Kernel Image ... OK   
> kernel loaded at 0x00080000, end = 0x001ac100   
> images.os.start = 0x0, images.os.end = 0x12c8bb   
> images.os.load = 0x80000, load\_end = 0x1ac100   
> ERROR: new format image overwritten - must RESET the board to recover  
> resetting ...   
> Command failed, result=-1

##### 3.4 重新规划内存的使用

原来在xprj\_uImage.itb中，我们指定Kernel image的load地址是0x80000，也就是说，u-boot在boot kernel之前，需要将kernel Image从itb文件中加载到load地址。但是，我们将itb文件放到0x0地址了，发生了覆盖，u-boot不允许，所以我们需要重新规划一下内存的使用，如下：

> 1）u-boot要在0x11000000（272M的位置）执行，并被relocated到DDR的底端。
>
> 2）kernel要在0x0执行，假设给它分配100M（0x6400000）的代码空间
>
> 3）那么，我们可以把itb文件上传到0x6400000处：
>
> sudo ../tools/dfu/dfu bubblegum 0xe406b200 ../tools/actions/splboot.bin 1
>
> sudo ../tools/dfu/dfu bubblegum 0x6400000 ./out/xprj\_uImage.itb 0
>
> sudo ../tools/dfu/dfu bubblegum 0x11000000 out/u-boot/u-boot-dtb.bin 1

再次执行bootm，成功了：

> [xprj]# bootm 0x6400000  
> ## Current stack ends at 0x3ffbc4e0 \* kernel: cmdline image address = 0x06400000   
> ## Loading kernel from FIT Image at 06400000 ...   
> No configuration specified, trying default...   
> Found default configuration: ['conf@bubblegum96'](mailto:'conf@bubblegum96')  
> Using 'conf@bubblegum96' configuration   
> Trying 'kernel@arm64' kernel subimage   
> Description: Unify(TODO) ARM64 Linux kernel   
> Type: Kernel Image   
> Compression: uncompressed   
> Data Start: 0x064000ec   
> Data Size: 1229056 Bytes = 1.2 MiB   
> Architecture: AArch64   
> OS: Linux   
> Load Address: 0x00080000   
> Entry Point: 0x00080000   
> Verifying Hash Integrity ... OK   
> kernel data at 0x064000ec, len = 0x0012c100 (1229056)   
> \* ramdisk: using config 'conf@bubblegum96' from image at 0x06400000   
> \* ramdisk: no 'ramdisk' in config   
> \* fdt: using config 'conf@bubblegum96' from image at 0x06400000   
> ## Checking for 'FDT'/'FDT Image' at 06400000   
> ## Loading fdt from FIT Image at 06400000 ...   
> Using 'conf@bubblegum96' configuration   
> Trying 'fdt@bubblegum96' fdt subimage   
> Description: Flattened Device Tree blob for Bubblegum-96   
> Type: Flat Device Tree   
> Compression: uncompressed   
> Data Start: 0x0652c2b8   
> Data Size: 181 Bytes = 181 Bytes   
> Architecture: AArch64   
> Verifying Hash Integrity ... OK   
> Can't get 'load' property from FIT 0x06400000, node: offset 1229352, name fdt@bubblegum96 (FDT\_ERR\_NOTFOUND)   
> Booting using the fdt blob at 0x652c2b8   
> of\_flat\_tree at 0x0652c2b8 size 0x000000b5   
> Initial value for argc=3   
> Final value for argc=3   
> Loading Kernel Image ... OK   
> kernel loaded at 0x00080000, end = 0x001ac100   
> using: FDT   
> ## initrd\_high = 0x3fffffff, copy\_to\_ram = 1   
> ramdisk load start = 0x00000000, ramdisk load end = 0x00000000   
> ## device tree at 000000000652c2b8 ... 000000000652c36c (len=12469 [0x30B5])   
> Loading Device Tree to 000000003ffb8000, end 000000003ffbb0b4 ... OK   
> Initial value for argc=3   
> Final value for argc=3   
> ## Transferring control to Linux (at address 80000)...   
> Starting kernel ...

从日志上可以看出：u-boot将kernel image加载到了load address（0x00080000）到0x001ac100的位置；由于我们没有指定FDT的加载地址，u-boot将它加载到了将FDT加载到了memory的高地址（0x3ffb8000）。

##### 3.5 点亮LED，确认kernel执行成功

参考“[X-010-UBOOT-使用booti命令启动kernel(Bubblegum-96平台)](/x_project/bubblegum_uboot_booti.html)”有关的说明，插入点亮LED的代码，确认OK。

#### 4. 总结和思考

经过上面的实践，我们得出如下的经验：

> 1）对uImage中某一个Image来说，u-boot会将它重新load到“load address“，因此，需要确保load address和uImage所在的memory区域不能重叠。
>
> 2）对于那些可被指定的Image，u-boot会跳转到”entry point“处执行，例如linux kernel。对ARM64而言，”load address“和”entry address“是相同的。

另外，其实FIT uImage离unify kernel的目标还有一段距离，因为当前还有如下的不足：

> 1）虽然可以指定多个Image，但只要其中的某一个（或者多个）Image不存在，make uImage就无法执行成功。
>
> 2）以ARM64为例，假如kernel Image都是同一个，区别是不同版型的load address和entry point不同，要怎么办？.its的语法并没有照顾到这种场景。
>
> 3）u-boot将Image文件从.itb文件解除之后，会重新把它们copy到一个新的地址（load address），这等于凭空多了一次memory copy，这些动作本来可以由bootloader在从存储器中copy的时候一次性完成，这岂不是一种浪费？

希望在后续的实践过程中，逐渐解决上述问题。

#### 5. 参考文档

[1] [https://github.com/wowotechX/doc/blob/master/README.bubblegum96](https://github.com/wowotechX/doc/blob/master/README.bubblegum96 "https://github.com/wowotechX/doc/blob/master/README.bubblegum96")

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/x_project/bubblegum_uboot_bootm.html)。

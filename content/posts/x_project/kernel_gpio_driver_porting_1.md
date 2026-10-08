---
title: "X-025-KERNEL-Linux gpio driver的移植之基本功能"
date: 2017-09-13T22:18:00+08:00
url: "/x_project/kernel_gpio_driver_porting_1.html"
gid: "410"
emlog_type: "blog"
summary: "\r\n\t本文将基于本站GPIO subsystem[1]相关的文章，结合”X Project”的开发过程，实现一个简单的gpio driver，并利用gpiolib提供的sysfs api进行简单的测试，进而加深对gpio相关概念的理解。\r\n\r\n\r\n\t注1：本文后续的描述，kernel基于本站“X Project”所使用的kernel版本，硬件基于 ”X Project”所使用的“Bubbugum-"
author: "wowo"
category: "X Project"
category_alias: "x_project"
tags: ["sysfs", "driver", "GPIO", "porting", "gpiolib"]
views: 25018
comment_count: 2
aliases:
  - "/x_project/410.html"
  - "/410.html"
---

## 1. 前言

本文将基于本站GPIO subsystem[1]相关的文章，结合”[X Project](/sort/x_project)”的开发过程，实现一个简单的gpio driver，并利用gpiolib提供的sysfs api进行简单的测试，进而加深对gpio相关概念的理解。

注1：本文后续的描述，kernel基于本站“[X Project](/sort/x_project)”所使用的kernel版本，硬件基于 ”[X Project](/sort/x_project)”所使用的“Bubbugum-96”平台[2]。

## 2. 添加gpio driver的驱动框架

kernel中所有驱动的开发都是一个套路，包括如下几个步骤：

a）新建driver文件（例如drivers/gpio/gpio-owl.c）并从其它地方copy一个架子（例如从drivers/pinctrl/pinctrl-owl.c中，并将pinctrl替换为gpio）。

b）修改drivers/gpio/Kconfig和drivers/gpio/Makefile，将这个新的driver添加到编译体系中：

> $ git diff drivers/gpio/   
> ...   
> --- a/drivers/gpio/Kconfig   
> +++ b/drivers/gpio/Kconfig   
> @@ -342,6 +342,12 @@ config GPIO\_OMAP   
> help   
> Say yes here to enable GPIO support for TI OMAP SoCs.   
> +config GPIO\_OWL   
> + bool "GPIO driver for Actions OWL soc"   
> + default y if ARCH\_OWL   
> + help   
> + This selects the gpio driver for Actions OWL soc.   
> +  
> ...   
>   
> --- a/drivers/gpio/Makefile   
> +++ b/drivers/gpio/Makefile   
> ...   
> +obj-$(CONFIG\_GPIO\_OWL) += gpio-owl.o  
> obj-$(CONFIG\_GPIO\_PCA953X) += gpio-pca953x.o   
> ...

注2：参考drivers/gpio/Kconfig中有关的注释，为了使我们的driver看着更专业、更规范，我们需要以字母为顺序把我们新的driver放到合适的位置：

> config GPIO\_GENERIC   
> tristate   
> # put drivers in the right section, in alphabetical order   
> # This symbol is selected by both I2C and SPI expanders  
> config GPIO\_MAX730X   
> tristate

c）修改arch/arm64/Kconfig.platforms，选中ARCH\_REQUIRE\_GPIOLIB配置项，这样就会默认编译gpio有关的代码。

> vim@ubuntu:~/work/xprj/linux$ git diff arch/arm64/Kconfig.platforms   
> diff --git a/arch/arm64/Kconfig.platforms b/arch/arm64/Kconfig.platforms   
> index b03d2538..48c4ae2 100644   
> --- a/arch/arm64/Kconfig.platforms   
> +++ b/arch/arm64/Kconfig.platforms   
> @@ -178,6 +178,7 @@ config ARCH\_OWL   
> bool "Actions OWL 64-bit SoC Family"   
> select PINCTRL   
> select PINMUX   
> + select ARCH\_REQUIRE\_GPIOLIB  
> help   
> This enables support for Actions OWL based SoCs like the S900.

d）编译kernel，发现新的driver已经编译进来了

> vim@ubuntu:~/work/xprj/build$ make kernel   
> CHK include/generated/timeconst.h   
> CHK include/generated/asm-offsets.h   
> CALL /home/vim/work/xprj/linux/scripts/checksyscalls.sh   
> CHK include/generated/compile.h   
> CC drivers/gpio/gpio-owl.o  
> LD drivers/gpio/built-in.o   
> CC drivers/irqchip/irqchip.o   
> CC drivers/irqchip/irq-gic.o

至此GPIO driver的驱动框架已经成型（具体的patch如下），后续根据实际的硬件，往里面填充东西使其慢慢完善即可。

> <https://github.com/wowotechX/linux/commit/2e8b86d7f2e4e892d4a9e1d82cbaa6d3051cfa56>

## 3. 添加gpiochip

由[3]中的介绍可知，编写gpio driver驱动的主要工作就是使用gpiochip抽象gpio控制器，一般情况下，有两种抽象策略：

> a）使用一个gpiochip抽象并管理系统中所有的gpio。
>
> b）每个bank（有关bank的概念，熟悉gpio的同学应该都了解，这里就不解释了）使用一个gpiochip抽象（一个实现，多个实例）。

至于使用哪种策略，主要是由代码编写的方便与否决定的，可以自行发挥，这里以第二种为例。

gpiochip的实现比较简单，主要包括（可参考后面的patch)：

a）实现request和free接口，可交给pinctrl[4]（可以先什么都不做）。

b）实现direction\_input、direction\_output、get 、set等接口。

c）根据实际情况，填充其它字段。

> patch：<https://github.com/wowotechX/linux/commit/d05448f039f961f09226f8ef30cba6b706aa8c15>

## 4. 结合gpiolib提供的sysfs api调试

实现基本的功能之后，我们可以借助gpiolib提供的sysfs api进行简单的验证和测试，步骤如下：

#### 4.1 打开SYSFS配置项（CONFIG\_SYSFS）和GPIO\_SYSFS配置项（CONFIG\_GPIO\_SYSFS）

> make kernel-config
>
> File systems --->   
> Pseudo filesystems --->   
> d[\*] sysfs file system support
>
> Device Drivers --->   
> -\*- GPIO Support --->   
> [\*] /sys/class/gpio/... (sysfs interface)

结果如下：

> --- a/arch/arm64/configs/xprj\_defconfig   
> +++ b/arch/arm64/configs/xprj\_defconfig   
> ...   
> +CONFIG\_GPIO\_SYSFS=y  
> # CONFIG\_HWMON is not set   
> ...   
> -# CONFIG\_SYSFS is not set  
> # CONFIG\_MISC\_FILESYSTEMS is not set

#### 4.2 修改dts，增加gpio的node

注2：“Bubbugum-96”平台[2]平台中，pinctrl和gpio是同一个模块，控制寄存器都在一起，这里偷懒，不想区分哪个是pinctrl的、哪个是gpio的了，就使用相同的寄存器范围就行了。不过呢，这一来我们在代码中就不能使用devm\_ioremap\_resource进行寄存器映射（devm\_xxx类的接口具有排他性），要换成ioremap，具体请参考下面的改动。

> + gpioa: gpio@0xe01b0000 {   
> + compatible = "actions,s900-gpio";   
> + reg = <0 0="" 12="" 0xe01b0000="">;   
> + };   
> + gpiob: [gpio@0xe01b000c](mailto:gpio@0xe01b000c) {   
> + compatible = "actions,s900-gpio";   
> + reg = <0 0="" 12="" 0xe01b000c="">;   
> + };   
> ...

> --- a/drivers/pinctrl/pinctrl-owl.c   
> +++ b/drivers/pinctrl/pinctrl-owl.c   
> ...   
> - priv->membase = devm\_ioremap\_resource(dev, resource);   
> + priv->membase = ioremap(resource->start, resource\_size(resource));

以上4.1和4.2的修改可参考下面的patch：<https://github.com/wowotechX/linux/commit/3c8fa7f1076cc6786166b7c3c742ce19ec640c53>

#### 4.3 编译并在板子上运行

跑起来后发现有如下错误：

> [ 0.218562] gpio gpiochip1: GPIO integer space overlap, cannot add chip   
> [ 0.225124] gpiochip\_add\_data: GPIOs 0..31 (owl-gpio) failed to register   
> [ 0.231781] owl\_gpio e01b000c.gpio: Failed to add gpiochip   
> [ 0.237249] owl\_gpio: probe of e01b000c.gpio failed with error -16   
> [ 0.243437] owl\_gpio e01b0018.gpio: owl\_gpio\_probe   
> [ 0.248187] gpio gpiochip1: GPIO integer space overlap, cannot add chip   
> [ 0.254749] gpiochip\_add\_data: GPIOs 0..31 (owl-gpio) failed to register   
> [ 0.261437] owl\_gpio e01b0018.gpio: Failed to add gpiochip   
> [ 0.266906] owl\_gpio: probe of e01b0018.gpio failed with error -16

总结来说，原因有二：

1） 每一个gpio bank（4.2中的dts node）要对应一个gpiochip结构，我们上面的移植忽略了这个事情。

2）每一个gpiochip的base要小心维护，要在整个gpio subsystem中唯一，因为sysfs api以base命名相应的gpiochip（可参考后面的介绍），并以base和nrgpio计算逻辑上的gpio number，我们可以简单的将base设置为0、32、64、等等。

修改的方法如下：

> diff --git a/arch/arm64/boot/dts/actions/s900-bubblegum.dts b/arch/arm64/boot/dts/actions/s900-bubblegum.dts   
> index 2c959d2..6119dbc 100644   
> --- a/arch/arm64/boot/dts/actions/s900-bubblegum.dts   
> +++ b/arch/arm64/boot/dts/actions/s900-bubblegum.dts   
> @@ -55,26 +55,32 @@   
> gpioa: gpio@0xe01b0000 {   
> compatible = "actions,s900-gpio";   
> reg = <0 0="" 12="" 0xe01b0000="">;   
> + base = <0>;  
> };   
> gpiob: gpio@0xe01b000c {   
> compatible = "actions,s900-gpio";   
> reg = <0 0="" 12="" 0xe01b000c="">;   
> + base = <32>;  
> };   
> ...   
>   
> diff --git a/drivers/gpio/gpio-owl.c b/drivers/gpio/gpio-owl.c   
> index f71bc7a..e32e292 100644   
> --- a/drivers/gpio/gpio-owl.c   
> +++ b/drivers/gpio/gpio-owl.c   
> @@ -20,6 +20,7 @@   
> #include    
> #include    
> #include    
>  +#include    
> #include    
> #include
>
> @@ -34,6 +35,8 @@
>
> struct owl\_gpio\_priv {   
> void \_\_iomem \*membase;   
> +   
> + struct gpio\_chip gpiochip;  
> };
>
> ...   
>   
> @@ -166,7 +169,10 @@ static int owl\_gpio\_probe(struct platform\_device \*pdev)   
> return PTR\_ERR(priv->membase);   
> }
>
> - ret = devm\_gpiochip\_add\_data(dev, &owl\_gpio\_chip, priv);   
> + memcpy(&priv->gpiochip, &owl\_gpio\_chip, sizeof(struct gpio\_chip));   
> + of\_property\_read\_u32(dev->of\_node, "base", &priv->gpiochip.base);  
> +   
> + ret = devm\_gpiochip\_add\_data(dev, &priv->gpiochip, priv);   
> if (ret < 0) {   
> dev\_err(dev, "Failed to add gpiochip\n");   
> return ret;

修改后再次编译运行，已经可以正确probe了：

> [ 0.209124] owl\_gpio e01b0000.gpio: owl\_gpio\_probe   
> [ 0.213968] owl\_gpio e01b000c.gpio: owl\_gpio\_probe   
> [ 0.218718] owl\_gpio e01b0018.gpio: owl\_gpio\_probe   
> [ 0.223468] owl\_gpio e01b0024.gpio: owl\_gpio\_probe   
> [ 0.228249] owl\_gpio e01b0030.gpio: owl\_gpio\_probe   
> [ 0.232999] owl\_gpio e01b00f0.gpio: owl\_gpio\_probe

#### 4.4 通过sysfs api控制gpio点亮、熄灭LED灯

由于当前测试环境（bubblegum96）的rootfs的是在ramdisk中，因此在系统启动后，我们需要手动创建/sys目录并挂载sysfs，如下：

> mkdir /sys   
> mount -t sysfs /sys /sys

sysfs挂在后可以在gpio class下看到gpiolib提供的sysfs api，如下：

> ls /sys/class/gpio   
> export gpiochip128 gpiochip32 gpiochip96   
> gpiochip0 gpiochip160 gpiochip64 unexport

参考[5]中的介绍，我们可以将需要使用的gpio number（逻辑number）写入到export文件，这样就可以将该gpio申请出来，并体现在/sys/class/gpio/目录中。以GPIOA19（LED0）为例（gpio的base是0，因此逻辑number也是19）：

> / # echo 19 > /sys/class/gpio/export   
> sh: write error: No such device

又出现错误，经过排查，原来我们的request接口还没有正确实现，没关系，先返回OK（0）：

> static int owl\_gpio\_request(struct gpio\_chip \*chip, unsigned offset)   
> {   
> - return pinctrl\_request\_gpio(offset);   
> + //return pinctrl\_request\_gpio(offset);   
> + return 0;  
> }   
> ...

再次测试，OK：

> echo 19 > /sys/class/gpio/export   
> / # ls /sys/class/gpio   
> lass/gpio   
> export gpiochip0 gpiochip160 gpiochip64 unexport   
> gpio19 gpiochip128 gpiochip32 gpiochip96

然后我们可以向“/sys/class/gpio/gpio19/direction ”中写入“out”字符串，将gpio的方向设置为输出，然后向/sys/class/gpio/gpio19/value中写入“1”或者“0”控制gpio的输出电平，如下：

> / # echo out > /sys/class/gpio/gpio19/direction   
> echo out > /sys/class/gpio/gpio19/di[ 36.780156] owl\_gpio e01b0000.gpio: offset 19, value 0   
> rection
>
> / # echo 1 > /sys/class/gpio/gpio19/value   
> echo 1 > /sys/class/gpio/gpio19/val[ 54.310562] owl\_gpio e01b0000.gpio: offset 19, value 1   
> ue   
> / # echo 0 > /sys/class/gpio/gpio19/value   
> > /sys/class/gpio/gpio19/valu[ 60.714062] owl\_gpio e01b0000.gpio: offset 19, value 0   
> e

然后观察LED灯，检查是否可以正确控制，如果可以则测试成功。

以上patch可参考：[https://github.com/wowotechX/linux/commit/30fcb89aabc7eef0043034262f76d3ebe4a9c789](https://github.com/wowotechX/linux/commit/30fcb89aabc7eef0043034262f76d3ebe4a9c789 "https://github.com/wowotechX/linux/commit/30fcb89aabc7eef0043034262f76d3ebe4a9c789")

## 5. 参考文档

[1] [/sort/gpio_subsystem](/sort/gpio_subsystem "/sort/gpio_subsystem")

[2] <https://github.com/96boards/documentation/blob/master/ConsumerEdition/Bubblegum-96/HardwareDocs/SoC_bubblegum96.pdf>

[3] [linux内核中的GPIO系统之（1）：软件框架](/gpio_subsystem/io-port-control.html)

[4] [linux内核中的GPIO系统之（5）：gpio subsysem和pinctrl subsystem之间的耦合](/gpio_subsystem/pinctrl-and-gpio.html)

[5] Documentation/gpio/sysfs.txt

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/x_project/kernel_gpio_driver_porting_1.html)。

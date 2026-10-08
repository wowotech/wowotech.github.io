---
title: "X-015-KERNEL-ARM generic timer driver的移植"
date: 2016-11-02T22:31:07+08:00
url: "/x_project/generic_timer_porting.html"
gid: "349"
emlog_type: "blog"
summary: "\r\n\t本文将基于“Linux时间子系统之（十七）：ARM \r\ngeneric timer驱动代码分析[1]”，以bubblegum-96平台为例，介绍ARM generic \r\ntimer的移植步骤。\r\n\r\n\r\n\t另外，我们在[2]中完成了ARM \r\nGIC驱动的移植，但还没有测试是否可用。刚好借助timer驱动，测试GIC是否可以正常工作，顺便理解Interrupt的使用方法。\r\n"
author: "wowo"
category: "X Project"
category_alias: "x_project"
tags: ["Linux", "Kernel", "内核", "timer", "porting", "generic"]
views: 12708
comment_count: 2
aliases:
  - "/x_project/349.html"
  - "/349.html"
---

## 1. 前言

本文将基于“[Linux时间子系统之（十七）：ARM generic timer驱动代码分析](/timer_subsystem/armgeneraltimer.html)[1]”，以bubblegum-96平台为例，介绍ARM generic timer的移植步骤。

另外，我们在[2]中完成了ARM GIC驱动的移植，但还没有测试是否可用。刚好借助timer驱动，测试GIC是否可以正常工作，顺便理解Interrupt的使用方法。

## 2. Generic timer硬件说明

有关ARM generic timer的技术细节，可参考[1]。本文所使用的bubblegum-96平台，其SOC包含了4个Cortex A53的core，支持CP15 type的Generic timer。为了驱动它，我们需要如下两个信息：

> 1）System counter的输入频率。
>
> 2）Per-CPU的timer和GIC之间的接口（即这些Timer的中断源以及中断触发方式）。参考[2]中的介绍，对于支持virtualization extension的SOC，每个cpu有四个timer：Non-secure PL1 physical timer，Secure PL1 physical timer，Non-secure PL2 physical timer和virtual timer ，因此将会有四个中断源。

不过，和我们移植GIC驱动[2]时遇到的问题一样，我们找不到bubblegum-96平台有关的信息（大家在开发自己的平台时，应该没有这些困扰），只能从开源出来的代码中[5]反推，结论如下：

> 1）System counter的输入频率为24MHz，这一点可以从[4]中推测出来，因为bubblegum-96开发板的晶振是24MHz，一般system counter直接使用晶振为输入时钟。
>
> 2）4个Per-CPU timer的中断源分别是：Non-secure PL1 physical timer----PPI 13，Secure PL1 physical timer----PPI 14，Non-secure PL2 physical timer----PPI 11，virtual timer----PPI 10。 它们都是低电平触发的方式。

## 3. Generic timer移植

#### 3.1 u-boot中的移植

记得我们在“[X-013-UBOOT-使能autoboot功能](/x_project/uboot_autoboot.html)”中调试u-boot的autoboot功能的时候，由于没有timer驱动，无法正确使用CONFIG\_BOOTDELAY（因为无法计时）。既然本文要在kernel中移植generic timer，就顺便提一下，在u-boot中支持ARM generic timer的方法。

其实很简单，对于ARM64平台来说，支持generic timer只需要知道System counter的输入频率，并通过COUNTER\_FREQUENCY宏定义告诉u-boot即可，如下（我们同时修改boot delay为5s，以验证timer功能）：

> /\* include/configs/bubblegum.h \*/
>
> @@ -74,7 +74,8 @@   
> #define CONFIG\_CMD\_BOOTI   
>   
> -#define CONFIG\_BOOTDELAY -2   
> +#define CONFIG\_BOOTDELAY 5  
> #define CONFIG\_BOOTCOMMAND "bootm 0x6400000"   
>   
> +#define COUNTER\_FREQUENCY (24000000) /\* 24MHz \*/   
> #endif

修改完成后，编译u-boot并启动kernel，就可以看到自动boot之前的倒计时了，说明timer添加成功：

> cd ~/work/xprj/build   
> make u-boot uImage   
> make spi-run
>
> make kernel-run

#### 3.2 kernel中的移植

在kernel中的移植也很简单，只需要修改dts文件，添加generic timer的节点，并提供第2章所描述的硬件信息即可：

> /\* ./arch/arm64/boot/dts/actions/s900-bubblegum.dts \*/
>
> +#include   
> +   
> / {   
> model = "Bubblegum-96 Development Board";   
> compatible = "actions,s900-bubblegum", "actions,s900";   
> +   
> + timer {   
> + compatible = "arm,armv8-timer";   
> + interrupts = ,   
> + ,   
> + ,   
> + ;   
> + clock-frequency = <24000000>;   
> + };  
> };

说明如下：

1）为了使用GIC有关的信息，我们需要包含“include/dt-bindings/interrupt-controller/arm-gic.h”头文件。

2）timer节点的compatible字段为"arm,armv8-timer"，表明我们是armv8 generic timer。

3）通过clock-frequency字段指定system counter的输入频率，这里为24000000（24MHz）。

4）interrupts字段指定了该设备所使用的中断源，可以是一个，也可以是多个，按照第2章的介绍，这里共有4个。参考[2]中的介绍，GIC的interrupt-cell为3，分别是：

> 第一个cell：PPI或SPI，此处均为PPI；
>
> 第二个cell，中断号，这里分别为13，14，11，10；
>
> 第三个cell，终端flag，这里需要包含一个GIC强制要求的----GIC\_CPU\_MASK\_SIMPLE(4)，另外就是中断触发类型，此处全是低电平触发。

## 4. 测试和验证

## 4.1 编译及debug

修改完dts文件，编译并运行kernel，GIC移植[4]时最后的kernel panic（如下）不见了：

> clocksource\_probe: no matching clocksources found   
> Kernel panic - not syncing: Unable to initialise architected timer.
>
> ---[ end Kernel panic - not syncing: Unable to initialise architected timer.

取而代之的是：

> NR\_IRQS:64 nr\_irqs:64 0   
> arch\_timer: No interrupt available, giving up  
> sched\_clock: 64 bits at 250 Hz, resolution 4000000ns, wraps every 9007199254000000ns   
> Calibrating delay loop (skipped), value calculated using timer frequency.. 48.00 BogoMIPS (lpj=96000)   
> pid\_max: default: 4096 minimum: 301   
> Mount-cache hash table entries: 4096 (order: 3, 32768 bytes)   
> Mountpoint-cache hash table entries: 4096 (order: 3, 32768 bytes)   
> No CPU information found in DT   
> ASID allocator initialised with 65536 entries   
> Brought up 1 CPUs   
> SMP: Total of 1 processors activated.   
> CPU: All CPU(s) started at EL2   
> clocksource: jiffies: mask: 0xffffffff max\_cycles: 0xffffffff, max\_idle\_ns: 7645041785100000 ns   
> vdso: 2 pages (1 code @ ffffff8008185000, 1 data @ ffffff80081c4000)   
> DMA: preallocated 256 KiB pool for atomic allocations   
> workingset: timestamp\_bits=60 max\_order=19 bucket\_order=0   
> Failed to find cpu0 device node   
> Unable to detect cache hierarchy from DT for CPU 0   
> Warning: unable to open an initial console.   
> Freeing unused kernel memory: 116K (ffffff80081a0000 - ffffff80081bd000)   
> This architecture does not have kernel memory protection.   
> Kernel panic - not syncing: No working init found. Try passing init= option to kernel. See Linux Documentation/init.txt for guidance.   
> Kernel Offset: disabled   
> Memory Limit: none   
> ---[ end Kernel panic - not syncing: No working init found. Try passing init= option to kernel. See Linux Documentation/init.txt for guidance.

“arch\_timer: No interrupt available, giving up”好像还有哪里不对劲，好像我们在第3章dts中指定的interrupts字段，没有被正常解析。没关系，根据[6]的介绍，打开所有的DEBUG输出，然后根据更为详细的日志，检查代码（过程略掉……），如下（从drivers/clocksource/arm\_arch\_timer.c开始）：

> CLOCKSOURCE\_OF\_DECLARE(armv8\_arch\_timer, "arm,armv8-timer", arch\_timer\_of\_init);   
> irq\_of\_parse\_and\_map(drivers/of/irq.c)   
> of\_irq\_parse\_one   
> of\_irq\_find\_parent

好像是找不到interrupt parent？原来是我们的dts还没有添加interrupt-parent字段，按照下面的代码增加：

> --- a/arch/arm64/boot/dts/actions/s900-bubblegum.dts   
> +++ b/arch/arm64/boot/dts/actions/s900-bubblegum.dts
>
> @@ -12,6 +12,8 @@
>
> model = "Bubblegum-96 Development Board";   
> compatible = "actions,s900-bubblegum", "actions,s900";   
> + interrupt-parent = <&gic>;   
> +  
> #address-cells = <2>;   
> #size-cells = <2>;

再次编译执行，异常消失了，算是移植完成了吧。

#### 4.2 测试

测试的方法很简单，我们把printk的时间戳打开，如果可以正确显示时间戳，则说明移植成功。打开printk时间戳的方法如下：

> cd ~/work/xprj/build;   
> make kernel-config
>
> Kernel hacking --->   
> printk and dmesg options --->   
> [\*] Show timing information on printks

然后编译并运行kernel，输出的日志如下：

> …
>
> [ 0.093281] Failed to find cpu0 device node
>
> [ 0.097437] Unable to detect cache hierarchy from DT for CPU 0
>
> [ 0.103562] Warning: unable to open an initial console.
>
> [ 0.108531] Freeing unused kernel memory: 116K (ffffff80081a0000 - ffffff80081bd000)
>
> [ 0.116156] This architecture does not have kernel memory protection.
>
> [ 0.122593] Kernel panic - not syncing: No working init found. Try passing init= option to kernel. See Linux Documentation/init.txt for guidance.
>
> [ 0.135656] Kernel Offset: disabled
>
> [ 0.139124] Memory Limit: none
>
> [ 0.142156] ---[ end Kernel panic - not syncing: No working init found. Try passing init= option to kernel. See Linux Documentation/init.txt for guidance.

成功了。

## 5. 参考文档

[1] [Linux时间子系统之（十七）：ARM generic timer驱动代码分析](/timer_subsystem/armgeneraltimer.html)

[2] [X-014-KERNEL-ARM GIC driver的移植](/x_project/gic_driver_porting.html)

[3] [bubblegum-96/SoC\_bubblegum96.pdf](https://github.com/96boards/documentation/blob/master/ConsumerEdition/Bubblegum-96/AdditionalDocs/SoC_bubblegum96.pdf)

[4] [bubblegum-96/HardwareManual\_Bubblegum96.pdf](https://github.com/uCRDev/documentation/blob/master/ConsumerEdition/Bubblegum-96/AdditionalDocs/HardwareManual_Bubblegum96_S900_V1.1.pdf)

[5] <https://github.com/96boards-bubblegum/linux/blob/bubblegum96-3.10/arch/arm64/boot/dts/s900.dtsi>

[6] [Linux kernel debug技巧----开启DEBUG选项](/linux_application/kernel_debug_enable.html)

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/x_project/generic_timer_porting.html)。

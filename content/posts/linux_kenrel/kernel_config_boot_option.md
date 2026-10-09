---
title: "Linux kernel内核配置解析(5)_Boot options(基于ARM64架构)"
date: 2016-08-12T22:46:06+08:00
url: "/linux_kenrel/kernel_config_boot_option.html"
gid: "325"
emlog_type: "blog"
summary: "本文将介绍ARM64架构下，Linux kernel和启动有关的配置项。 注1：本系列文章使用的Linux kernel版本是“ X Project ”所用的“ Linux 4.6-rc5 ”，具体可参考“ https://github.com/wowotechX/linux.git ”。"
author: "wowo"
category: "Linux内核分析"
category_alias: "linux_kenrel"
tags: ["Linux", "内核", "boot", "配置项", "menuconfig"]
views: 17381
comment_count: 2
aliases:
  - "/linux_kenrel/325.html"
  - "/325.html"
---

#### 1. 前言

本文将介绍ARM64架构下，Linux kernel和启动有关的配置项。

注1：本系列文章使用的Linux kernel版本是“[X Project](/forum/)”所用的“[Linux 4.6-rc5](https://github.com/wowotechX/linux/commit/02da2d72174c61988eb4456b53f405e3ebdebce4)”，具体可参考“<https://github.com/wowotechX/linux.git>”。

#### 2. Kconfig文件

ARM64架构中和Boot有关的配置项，非常简单，主要包括ACPI、命令行参数和UEFI几种。这些配置项位于“ [arch/arm64/Kconfig](https://github.com/wowotechX/linux/blob/x_integration/arch/arm64/Kconfig)”中，具体如下：

```
  1: menu "Boot options"
  2: 
  3: config ARM64_ACPI_PARKING_PROTOCOL
  4: 	bool "Enable support for the ARM64 ACPI parking protocol"
  5: 	depends on ACPI
  6: 	help
  7: 	  Enable support for the ARM64 ACPI parking protocol. If disabled
  8: 	  the kernel will not allow booting through the ARM64 ACPI parking
  9: 	  protocol even if the corresponding data is present in the ACPI
 10: 	  MADT table.
 11: 
 12: config CMDLINE
 13: 	string "Default kernel command string"
 14: 	default ""
 15: 	help
 16: 	  Provide a set of default command-line options at build time by
 17: 	  entering them here. As a minimum, you should specify the the
 18: 	  root device (e.g. root=/dev/nfs).
 19: 
 20: config CMDLINE_FORCE
 21: 	bool "Always use the default kernel command string"
 22: 	help
 23: 	  Always use the default kernel command string, even if the boot
 24: 	  loader passes other arguments to the kernel.
 25: 	  This is useful if you cannot or don't want to change the
 26: 	  command-line options your boot loader passes to the kernel.
 27: 
 28: config EFI_STUB
 29: 	bool
 30: 
 31: config EFI
 32: 	bool "UEFI runtime support"
 33: 	depends on OF && !CPU_BIG_ENDIAN
 34: 	select LIBFDT
 35: 	select UCS2_STRING
 36: 	select EFI_PARAMS_FROM_FDT
 37: 	select EFI_RUNTIME_WRAPPERS
 38: 	select EFI_STUB
 39: 	select EFI_ARMSTUB
 40: 	default y
 41: 	help
 42: 	  This option provides support for runtime services provided
 43: 	  by UEFI firmware (such as non-volatile variables, realtime
 44:           clock, and platform reset). A UEFI stub is also provided to
 45: 	  allow the kernel to be booted as an EFI application. This
 46: 	  is only useful on systems that have UEFI firmware.
 47: 
 48: config DMI
 49: 	bool "Enable support for SMBIOS (DMI) tables"
 50: 	depends on EFI
 51: 	default y
 52: 	help
 53: 	  This enables SMBIOS/DMI feature for systems.
 54: 
 55: 	  This option is only useful on systems that have UEFI firmware.
 56: 	  However, even with this option, the resultant kernel should
 57: 	  continue to boot on existing non-UEFI platforms.
 58: 
 59: endmenu
```

#### 3. 配置项说明

注2：Linux kernel的配置项虽然众多，但大多使用默认值就可以。因此在kernel移植和开发的过程中，真正需要关心的并不是特别多。对于那些常用的、需要关心的配置项，我会在分析文章中用黄色背景标注。

##### 3.1 ACPI有关的配置项

|  |  |  |
| --- | --- | --- |
| 配置项 | 说明 | 默认值 |
| CONFIG\_ARM64\_ACPI\_    PARKING\_PROTOCOL | 是否支持“ARM64 ACPI parking protocol”。关于ACPI和parking protocol，有机会的话我们会在其它文章中分析，这里不需要过多关注。 | 依赖于CONFIG\_ACPI |

##### 3.2 Kernel命令行参数有关的配置项

|  |  |  |
| --- | --- | --- |
| 配置项 | 说明 | 默认值 |
| CONFIG\_CMDLINE | 内核默认的命令行参数。设置该参数后，可以不需要bootloader传递（开始porting kernel的时候比较有用，因为不能保证bootloader可以正确传递^\_^） | 无 |
| CONFIG\_CMDLINE\_FORCE | 强制使用内核默认的命令行参数（可以忽略bootloader传递来的）；    一般在kernel开发的过程中，用来测试某些新的命令行参数（先不修修改bootloader传递的内容）。 | 无 |

注3：如果Kconfig没有通过“default”关键字为某个配置项指定默认值，那么生成的.config文件中就不会出现该配置项，也就是变相的“禁止”了。后同。

##### 3.3 UEFI有关的配置项

|  |  |  |
| --- | --- | --- |
| 配置项 | 说明 | 默认值 |
| CONFIG\_EFI\_STUB | 用于支持EFI启动；    使能该配置项之后，会修改Kenrel bzImage header，把kernel Image变成一个可以被EFI运行的PE/COFF Image。    具体可参考Documentation/efi-stub.txt中的介绍。 | 无 |
| CONFIG\_EFI | 支持一些由UEFI Firmware提供的、运行时的服务，如RTC、reset等；    该配置项依赖Open Firmware（device tree），并且有很多的关联项（可以参考Kconfig文件中的select关键字）；    另外，有意思的是（参考第2章Kconfig文件中的“depends on OF && !CPU\_BIG\_ENDIAN”），该配置项只能在小端CPU中才能使用。有空可以研究一下为什么。 | y |
| CONFIG\_DMI | 用于控制是否支持“SMBIOS/DMI feature”，依赖于CONFIG\_EFI；    需要注意的是，就算使能了该配置项，kernel也需要能够在其它非UEFI环境下正常启动。 | y |
DMI

#### 4. 参考文档

[1] UEFI,[/armv8a_arch/UEFI.html](/armv8a_arch/UEFI.html "/armv8a_arch/UEFI.html")

[2] ACPI,[https://zh.wikipedia.org/zh-cn/%E9%AB%98%E7%BA%A7%E9%85%8D%E7%BD%AE%E4%B8%8E%E7%94%B5%E6%BA%90%E6%8E%A5%E5%8F%A3](https://zh.wikipedia.org/zh-cn/%E9%AB%98%E7%BA%A7%E9%85%8D%E7%BD%AE%E4%B8%8E%E7%94%B5%E6%BA%90%E6%8E%A5%E5%8F%A3 "https://zh.wikipedia.org/zh-cn/%E9%AB%98%E7%BA%A7%E9%85%8D%E7%BD%AE%E4%B8%8E%E7%94%B5%E6%BA%90%E6%8E%A5%E5%8F%A3")

[3] SMBIOS/DMI,[http://www.dmtf.org/cn/standards/smbios](http://www.dmtf.org/cn/standards/smbios "http://www.dmtf.org/cn/standards/smbios")

*原创文章，转发请注明出处。蜗窝科技*，[www.wowotech.net](/linux_kenrel/kernel_config_boot_option.html)。

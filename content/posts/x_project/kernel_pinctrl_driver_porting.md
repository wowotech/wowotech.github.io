---
title: "X-023-KERNEL-Linux pinctrl driver的移植"
date: 2017-07-14T21:58:51+08:00
url: "/x_project/kernel_pinctrl_driver_porting.html"
gid: "401"
emlog_type: "blog"
summary: "\r\n\t本文是“linux内核中的GPIO系统之（4）：pinctrl驱动的理解和总结”的一个实例，结合”X Project”的开发过程，介绍pinctrl driver的移植步骤，进而加深对pinctrl framework的理解。\r\n\r\n\r\n\t注1：本文后续的描述，kernel基于本站“X Project”所使用的kernel版本[4]，硬件基于 ”X Project”所使用的“Bubbugum"
author: "wowo"
category: "X Project"
category_alias: "x_project"
tags: ["Linux", "Kernel", "driver", "porting", "pinctrl"]
views: 11890
comment_count: 0
aliases:
  - "/x_project/401.html"
  - "/401.html"
---

## 1. 前言

本文是“[linux内核中的GPIO系统之（4）：pinctrl驱动的理解和总结](/gpio_subsystem/pinctrl-driver-summary.html)”的一个实例，结合”[X Project](/sort/x_project)”的开发过程，介绍pinctrl driver的移植步骤，进而加深对pinctrl framework的理解。

注1：本文后续的描述，kernel基于本站“[X Project](/sort/x_project)”所使用的kernel版本[4]，硬件基于 ”[X Project](/sort/x_project)”所使用的“Bubbugum-96”平台。

## 2. pinctrl driver的移植步骤

#### 2.1 添加pinctrl driver在驱动模型中的框架

在linux kernel中，pin controller也是一个普通的platform device，因此需要基于platform设备的框架（可参考[1]）添加自身的驱动模型。对于这些单纯的设备，可以直接用一些标准化的接口来完成，如下（都是轻车熟路的东西，不再解释了）：

---->drivers/pinctrl/pinctrl-owl.c

|  |
| --- |
| /\*============================================================================     \* platform driver     \*==========================================================================\*/     static const struct of\_device\_id owl\_pinctrl\_of\_match[] = {     {     .compatible = "actions,s900-pinctrl",     },     {     },     };     MODULE\_DEVICE\_TABLE(of, owl\_pinctrl\_of\_match);        static int \_\_init owl\_pinctrl\_probe(struct platform\_device \*pdev)     {     return 0;     }        static void \_\_exit owl\_pinctrl\_remove(struct platform\_device \*pdev)     {     }        static struct platform\_driver owl\_pinctrl\_platform\_driver = {     .probe = owl\_pinctrl\_probe,     .remove = owl\_pinctrl\_remove,     .driver = {     .name = "owl\_pinctrl",     .of\_match\_table = owl\_pinctrl\_of\_match,     },     };     module\_platform\_driver(owl\_pinctrl\_platform\_driver);        MODULE\_ALIAS("platform driver: owl\_pinctrl");     MODULE\_DESCRIPTION("pinctrl driver for owl seria soc(s900, etc.)");     MODULE\_AUTHOR("wowo<wowo@wowotech.net>");     MODULE\_LICENSE("GPL v2"); |

（另外，需要编辑drivers/pinctrl中的Kconfig和Makefile文件，加入我们新的pinctrl driver，并更改”[X Project](/sort/x_project)”的kernel配置项，加入该driver的编译，具体步骤略，代码可参考如下的patch：[https://github.com/wowotechX/linux/commit/45ca29b3680db7b6d62735439a0ef93ab9797537](https://github.com/wowotechX/linux/commit/45ca29b3680db7b6d62735439a0ef93ab9797537 "https://github.com/wowotechX/linux/commit/45ca29b3680db7b6d62735439a0ef93ab9797537"),

[https://github.com/wowotechX/linux/commit/749f114564765025d907618d7306bc668c0a0a93](https://github.com/wowotechX/linux/commit/749f114564765025d907618d7306bc668c0a0a93 "https://github.com/wowotechX/linux/commit/749f114564765025d907618d7306bc668c0a0a93")）。

#### 2.2 添加pinctrl driver自身的框架

参考“Documentation/pinctrl.txt[2]"中的示例，创建一个struct pinctrl\_desc变量，并在probe中调用pinctrl\_register注册到kernel中。

另外，为了在同一个driver中支持多个soc，可以将struct pinctrl\_desc变量的指针保存在每个soc的match table中，并在probe中借助of\_device\_get\_match\_data将其获取出来（这是device tree时代的惯用伎俩，大家可以多使用），如下黄色背景所示：

|  |
| --- |
| static const struct of\_device\_id owl\_pinctrl\_of\_match[] = {     {     .compatible = "actions,s900-pinctrl",    .data = &s900\_desc,    },     {     },     };  ...  static int \_\_init owl\_pinctrl\_probe(struct platform\_device \*pdev)     {     ...  desc = of\_device\_get\_match\_data(dev);    if (desc == NULL) {     dev\_err(dev, "device get match data failed\n");     return -ENODEV;     }  pctl = pinctrl\_register(desc, dev, NULL);    ...     } |

可以直接从Documentation/pinctrl.txt中copy过来，将foo换成自己平台的代号（如这里的s900），然后在owl\_pinctrl\_probe中调用pinctrl\_register注册即可。

以上代码可参考如下的patch：[https://github.com/wowotechX/linux/commit/9ce89fe7e5d68f2d84dab39af0665acfc3b62751](https://github.com/wowotechX/linux/commit/9ce89fe7e5d68f2d84dab39af0665acfc3b62751 "https://github.com/wowotechX/linux/commit/9ce89fe7e5d68f2d84dab39af0665acfc3b62751")

#### 2.3 定义管脚（pin）

driver框架确定了之后，就简单了，根据[3]中的介绍，一个一个的添加各种软件抽象就行了。例如可以根据自己平台的实际情况，定义管脚。

注2：这里以“Bubbugum-96”平台为例，硬件有关的说明可参考之前的文章。另外，为了说明pinctrl driver的编写过程，这里简化一下，暂时只关心UART5有关的pin，其它的后面用的时候再加就行了。

根据原理图，uart5有关的pin脚包括（好东西，足够我们把pinctrl的原理展示完了）：

> GPIOA25/UART5\_RX/SENS0\_VSYNC/PWM2（A7）   
> GPIOA27/UART5\_TX/SENS0\_HSYNC/PWM2（D8）   
> GPIOA28/UART2\_RX/UART5\_RX/SD0\_D0（C5）   
> GPIOA29/UART2\_TX/UART5\_TX/SD0\_D1（B6）   
> GPIOF6/UART5\_RX/UART3\_RTSB（G2）   
> GPIOF7/UART5\_TX/UART3\_CTSB（G1）

名字，好办，就用A7、D8之类的就行了，编号怎么办呢？

先随便定吧（后面可能会根据寄存器的特性调整），直接用字母（转成数字，A是0，B是1，等等）乘以10加数字（数字好像是从1开始，那就数字减一），即：

> A7 = （1 – 1）\* 10 + （7 – 1）= 6   
>  D8 = (4 – 1) \* 10 + (8 – 1) = 37   
>  C5 = (3 – 1) \* 10 + (5 - 1) = 24   
>  B6 = (2 – 1) \* 10 + (6 – 1) = 15   
>  G2 = (7 – 1) \* 10 + (2 – 1) = 61   
>  G1 = (7 – 1) \* 10 + (1 – 1) =60

最终定义出来的管脚如下：

|  |
| --- |
| static const struct pinctrl\_pin\_desc s900\_pins[] = {     PINCTRL\_PIN(6, "A7"),     PINCTRL\_PIN(15, "B6"),     PINCTRL\_PIN(24, "C5"),     PINCTRL\_PIN(37, "D8"),     PINCTRL\_PIN(60, "G1"),     PINCTRL\_PIN(61, "G2"),     }; |

#### 2.4 定义pin group

暂时不考虑GPIO，上面6个pin可以分解出如下groups（麻雀虽小五脏俱全啊！不过简单起见，这里只关注UART5有关的group，因为其它group可能会涉及更多的pin）：

> uart5\_0\_group，包括A7和D8两个pin，由bubblegum96的spec[4]可知，当MFP\_CTL1 寄存器（0xE01B0044）的bit28:26和bit25:23分别为001（UART5\_RX）和100（UART5\_TX）时，该group生效；
>
> uart5\_1\_group，包括C5和B6两个pin，由bubblegum96的spec[4]可知，当MFP\_CTL2 寄存器（0xE01B0048）的bit19:17和bit16:14分别为101（UART5\_RX）和101（UART5\_TX）时，该group生效；
>
> uart5\_2\_group，包括G2和G1两个pin，由bubblegum96的spec[4]可知，当MFP\_CTL2 寄存器（0xE01B0048）的bit21和bit20分别为1（UART5\_RX）和1（UART5\_TX）时，该group生效。

最后参考[2]中的例子，定义并注册struct pinctrl\_ops变量，具体可参考如下patch：[https://github.com/wowotechX/linux/commit/478f3fcf2fc950daa6fb85eb302f943a427f0878](https://github.com/wowotechX/linux/commit/478f3fcf2fc950daa6fb85eb302f943a427f0878 "https://github.com/wowotechX/linux/commit/478f3fcf2fc950daa6fb85eb302f943a427f0878")

#### 2.5 Pin configuration的设计

参考[4]中“5.7.3.24 PAD\_PULLCTL0 ”~“5.7.3.35 PAD\_SR2 ”章节有关pin configuration的描述，发现s900的pinconf有点特殊，是以特定的功能（function，例如UART0\_RX）为单位进行控制的，也就是说，对某一个功能来说，可能映射到不同的管脚上，但对它的配置，都是由相同的寄存器控制的。

基于这样的硬件框架，怎么去抽象pinconf的operations，值得思考。不过由于本文的例子（uart5）没有可配置的选项，所以我们就先略过这里。后面有机会再补回来吧（不影响我们对pinctrl的整体理解）。

#### 2.6 Pin multiplexing的设计

同理，参考[2]中的示例，首先抽象出Pin multiplexing中的functions，本文的例子中，暂时只有一个：uart5，定义如下：

|  |
| --- |
| /\* drivers/pinctrl/pinctrl-owl.c \*/  static const char \* const uart5\_groups[] = {     "uart5\_0\_grp", "uart5\_1\_grp", "uart5\_2\_grp"     };  static const struct owl\_pmx\_func s900\_functions[] = {     {     .name = "uart5",     .groups = uart5\_groups,     .num\_groups = ARRAY\_SIZE(uart5\_groups),     },     }; |

> 该function可以映射到三个不同的group中："uart5\_0\_grp", "uart5\_1\_grp", "uart5\_2\_grp"（它们的名字要和2.4中定义的groups name相同）。

然后，定义一个struct pinmux\_ops变量，并实现相应的回调函数，如下：

|  |
| --- |
| static struct pinmux\_ops s900\_pmxops = {     .get\_functions\_count = s900\_get\_functions\_count,     .get\_function\_name = s900\_get\_fname,     .get\_function\_groups = s900\_get\_groups,     .set\_mux = s900\_set\_mux,     .strict = true,     }; |

上面get\_functions\_count 、get\_function\_name以及get\_function\_groups三个函数比较简单，这里重点提一下set\_mux，它的原型如下：

> int (\*set\_mux) (struct pinctrl\_dev \*pctldev, unsigned func\_selector,   
>  unsigned group\_selector);

有两个参数：func\_selector，用于指定function的number（就是s900\_functions中的数组index）；group\_selector，用于指定group的number（就是2.4中介绍的s900\_groups的数组index）。pinctrl driver拿到这两个参数之后，怎么去配置寄存器使某个group的某个function生效呢？要根据具体的pin controller的硬件情况来定。以本文作为示例的s900为例，该SoC的Pin multiplexing的设置，并不需要function和group的一一对应，以uart5 function的group0为例，参考2.4中的介绍：

> 只要把MFP\_CTL1 寄存器（0xE01B0044）的bit28:26和bit25:23分别设置为001（UART5\_RX）和100（UART5\_TX），就可以使uart5的该group生效。

也就是说，s900 SoC可以单独以group为单位进行pinmux配置。那么我们在代码中可以把相应的寄存器配置信息和groups的定义绑定，在pinctrl core调用.set\_mux回调函数的时候，忽略 func\_selector，直接通过group\_selector获取相应的寄存器信息后，配置寄存器即可，如下：

> +struct owl\_pmx\_reginfo {   
>  + const unsigned \*offset;   
>  + const unsigned \*mask;   
>  + const unsigned \*val;   
>  +   
>  + unsigned num\_entries;   
>  +};   
>  +   
>  struct owl\_pinctrl\_group {   
>  const char \*name;   
>  const unsigned \*pins;   
>  unsigned num\_pins;   
>  +   
>  + const struct owl\_pmx\_reginfo \*reginfo;  
>  +};   
>   
>  ......   
>   
>  static const struct owl\_pinctrl\_group s900\_groups[] = {   
>  {   
>  .name = "uart5\_0\_grp",   
>  .pins = s900\_uart5\_0\_pins,   
>  .num\_pins = ARRAY\_SIZE(s900\_uart5\_0\_pins),   
>  + .reginfo = &s900\_uart5\_0\_reginfo,  
>  },   
>  {   
>  .name = "uart5\_1\_grp",   
>  .pins = s900\_uart5\_1\_pins,   
>  .num\_pins = ARRAY\_SIZE(s900\_uart5\_1\_pins),   
>  + .reginfo = &s900\_uart5\_1\_reginfo,  
>  },   
>  {   
>  .name = "uart5\_2\_grp",   
>  .pins = s900\_uart5\_2\_pins,   
>  .num\_pins = ARRAY\_SIZE(s900\_uart5\_2\_pins),   
>  + .reginfo = &s900\_uart5\_2\_reginfo,  
>  },   
>  };   
>   
>  ...
>
> +static int s900\_set\_mux(struct pinctrl\_dev \*pctldev, unsigned selector,   
>  + unsigned group)   
>  +{   
>  + int i;   
>  + uint32\_t val;   
>  +   
>  + struct owl\_pinctrl\_priv \*priv = pctldev->driver\_data;   
>  +   
>  + const struct owl\_pmx\_reginfo \*reginfo;   
>  +   
>  + reginfo = s900\_groups[gourp].reginfo;   
>  +   
>  + for (i = 0; i < reginfo->num\_entries; i++) {   
>  + val = readl(priv->mem\_base + reginfo->offset[i]);   
>  + val &= ~reginfo->mask[i];   
>  + val |= reginfo->val[i];   
>  + writel(val, priv->mem\_base + reginfo->offset[i]);  
>  + }   
>  +   
>  + return 0;   
>  +}

以上代码比较直接、简单，又和具体的硬件平台有关，我就不详细解释了，大家在编写自己平台的pinctrl driver时，可以具体情况具体对待。

以上可参考如下patch：[https://github.com/wowotechX/linux/commit/52d6b8337a31267fd9b158d5f1f9d9590a16f92d](https://github.com/wowotechX/linux/commit/52d6b8337a31267fd9b158d5f1f9d9590a16f92d "https://github.com/wowotechX/linux/commit/52d6b8337a31267fd9b158d5f1f9d9590a16f92d")。

#### 2.7 dt\_node\_to\_map的设计

上面的pinmux设计完成之后，我们需要提供一种机制，让consumer（这里为serial driver）可以方便的使用。这里介绍利用device tree的方法----步骤有三：

1）定义pinctrl device的dts node，并包含一个包含uart5 function的子节点（节点的格式可以自行决定，因为是自己解析），例如：

|  |
| --- |
| --- a/arch/arm64/boot/dts/actions/s900-bubblegum.dts     +++ b/arch/arm64/boot/dts/actions/s900-bubblegum.dts     @@ -39,9 +39,25 @@     clock-frequency = <24000000>;     };  + pinctrl@0xe01b0000 {     + compatible = "actions,s900-pinctrl";     + reg = <0 0="" 0xe01b0000="" 0x550="">;     +     + uart5\_state\_default: uart5\_default {     + pinmux {     + function = "uart5";     + group = "uart5\_0\_grp";     + };     + /\* others, TODO \*/     + };     + }; |

> 这里子节点的名字为uart5\_default（别名为uart5\_state\_default，以便consumer device的dts node引用），代表了一个pin state（相关概念可参考[3]中的介绍）；
>
> 简单期间，该state里面包含一个entry----pinmux，该entry有两个关键字，function和group，都是字符串类型的。

2）在pinctrl driver中，实现.dt\_node\_to\_map和.dt\_free\_map回调函数，其中.dt\_node\_to\_map用于将dts node中的信息转换为pin map，示例如下：

|  |
| --- |
| +static int s900\_dt\_node\_to\_map(struct pinctrl\_dev \*pctldev,     + struct device\_node \*np\_config,     + struct pinctrl\_map \*\*map,     + unsigned \*num\_maps)     +{    + int ret, child\_cnt;     +     + const char \*function;     + const char \*group;     +     + struct device \*dev = pctldev->dev;     + struct device\_node \*np;     +     + dev\_dbg(dev, "%s\n", \_\_func\_\_);     +     + \*map = NULL;     + \*num\_maps = 0;     +     + child\_cnt = of\_get\_child\_count(np\_config);     + dev\_dbg(dev, "child\_cnt %d\n", child\_cnt);     +     + if (child\_cnt == 0)     + return 0;     +     + \*map = kzalloc(sizeof(struct pinctrl\_map) \* child\_cnt, GFP\_KERNEL);     + if (\*map == NULL) {     + dev\_dbg(dev, "malloc failed\n");     + return -ENOMEM;     + }     +     + for\_each\_child\_of\_node(np\_config, np) {     + ret = of\_property\_read\_string(np, "function", &function);     + if (ret != 0)     + continue;     +     + ret = of\_property\_read\_string(np, "group", &group);     + if (ret != 0)     + continue;     +     + dev\_dbg(dev, "got a pinmux entry: %s-%s\n", function, group);     +     + (\*map)[\*num\_maps].type = PIN\_MAP\_TYPE\_MUX\_GROUP;     + (\*map)[\*num\_maps].data.mux.function = function;     + (\*map)[\*num\_maps].data.mux.group = group;     + (\*num\_maps)++;     + }     +     + return 0;     +} |

> 这个例子比较简单：
>
> 参数主要包括：np\_config，dts节点指针，对应上面的“uart5\_state\_default”；map，pinctrl map指针的指针，需要pinctrl driver申请空间；num\_maps，map个数的指针，driver可以修改该指针的值，告诉上层软件最终的map个数。
>
> 得到dts node指针之后，我们可以遍历该node下的所有子节点，并检查对应的子节点下是否有有效的function和group字符串，如果有，则代表找到了一个有效的entry，将相应的信息（function name和group name）保存在maps数组中的一个entry即可。

3）在对应的consumer的dts node中，引用上述的pinctrl state，如下：

|  |
| --- |
| serial5: serial@e012a000 {     compatible = "actions,s900-serial";     reg = <0 0="" 0xe012a000="" 0x2000="">; /\* UART5\_BASE \*/     interrupts = ;     +    + pinctrl-names = "default";     + pinctrl-0 = <&uart5\_state\_default>;     }; |

> 上面pinctrl-names指定为"defualt"，这样可以在设备probe的时候由kernel自行获取相应的pinctrl state并使之生效。
>
> 然后在pinctrl-0字段中填入pinctrl state的地址：&uart5\_state\_default。
>
> 最后serial driver在probe的时候，将会按照[3]中介绍过程（probe-->devm\_pinctrl\_get or pinctrl\_get-->create\_pinctrl-->pinctrl\_dt\_to\_map-->dt\_to\_map\_one\_config-->pctlops->dt\_node\_to\_map-->s900\_dt\_node\_to\_map），将该设备对应的pinctrl state保存下来，并通过pinctrl\_lookup\_state查找名称为"default“的state，调用pinctrl\_select\_state，使其生效。

以上代码可参考如下patch：[https://github.com/wowotechX/linux/commit/7c7b7b948b6f4eb25ef7926c89eb1199e07a7bc9](https://github.com/wowotechX/linux/commit/7c7b7b948b6f4eb25ef7926c89eb1199e07a7bc9 "https://github.com/wowotechX/linux/commit/7c7b7b948b6f4eb25ef7926c89eb1199e07a7bc9")。

## 3. 编译与调试

完成上面的移植工作之后，我们增加一些debug信息，并使能该driver的DEBUG宏，如下（具体可参考“[https://github.com/wowotechX/linux/commit/3acb915db41a4e87defa8b4ea412d92feff62c57](https://github.com/wowotechX/linux/commit/3acb915db41a4e87defa8b4ea412d92feff62c57 "https://github.com/wowotechX/linux/commit/3acb915db41a4e87defa8b4ea412d92feff62c57")”）：

|  |
| --- |
| --- a/drivers/pinctrl/pinctrl-owl.c     +++ b/drivers/pinctrl/pinctrl-owl.c     @@ -13,6 +13,8 @@     \* You should have received a copy of the GNU General Public License     \* along with this program. If not, see <<http://www.gnu.org/licenses/>>.     \*/     +#define DEBUG    +     #include      #include      #include      @@ -143,17 +145,23 @@ static const struct owl\_pinctrl\_group s900\_groups[] = {  static int s900\_get\_groups\_count(struct pinctrl\_dev \*pctldev)     {     + dev\_dbg(pctldev->dev, "%s\n", \_\_func\_\_);     +    return ARRAY\_SIZE(s900\_groups);     }    ... |

然后编译、运行起来，得到如下的log：

> [ 0.080093] DMA: preallocated 256 KiB pool for atomic allocations   
>  [ 0.086499] clocksource: Switched to clocksource arch\_sys\_counter   
>  [ 0.092437] Unpacking initramfs...   
>  [ 0.177156] Freeing initrd memory: 1044K (ffffffc07feaf000 - ffffffc07ffb4000)   
>  [ 0.182031] workingset: timestamp\_bits=60 max\_order=19 bucket\_order=0   
>  [ 0.188093] owl\_pinctrl e01b0000.pinctrl: owl\_pinctrl\_probe   
>  [ 0.193593] owl\_pinctrl e01b0000.pinctrl: s900\_get\_functions\_count   
>  [ 0.199749] owl\_pinctrl e01b0000.pinctrl: s900\_get\_fname, selector 0   
>  [ 0.206093] owl\_serial\_init   
>  [ 0.208874] owl\_pinctrl e01b0000.pinctrl: s900\_dt\_node\_to\_map   
>  [ 0.214562] owl\_pinctrl e01b0000.pinctrl: child\_cnt 1   
>  [ 0.219593] owl\_pinctrl e01b0000.pinctrl: got a pinmux entry: uart5-uart5\_0\_grp   
>  [ 0.226874] owl\_pinctrl e01b0000.pinctrl: s900\_get\_functions\_count   
>  [ 0.232999] owl\_pinctrl e01b0000.pinctrl: s900\_get\_fname, selector 0   
>  [ 0.239343] owl\_pinctrl e01b0000.pinctrl: s900\_get\_groups, selector 0   
>  [ 0.245749] owl\_pinctrl e01b0000.pinctrl: s900\_get\_groups\_count   
>  [ 0.251656] owl\_pinctrl e01b0000.pinctrl: s900\_get\_group\_name, selector 0   
>  [ 0.258406] owl\_pinctrl e01b0000.pinctrl: s900\_get\_group\_pins, selector 0   
>  [ 0.265156] owl\_pinctrl e01b0000.pinctrl: s900\_set\_mux, selector 0, group 0   
>  [ 0.272093] owl\_pinctrl e01b0000.pinctrl: offset 44, mask 1c000000, val 4000000   
>  [ 0.279468] owl\_pinctrl e01b0000.pinctrl: offset 44, mask 3800000, val 2000000  
>  [ 0.286749] owl\_serial e012a000.serial: owl\_serial\_probe   
>  [ 0.292062] e012a000.serial: ttyS5 at MMIO 0xe012a000 (irq = 5, base\_baud = 0) is a unknown   
>  [ 0.300343] console [ttyS5] enabled   
>  [ 0.300343] console [ttyS5] enabled

大功告成！！后续其它的功能，在需要的时候慢慢完善就行了~~

## 4. 总结

经过上面的步骤，我们开发了一个简单的pinctrl driver，并通过consumer的dts node将其绑定。这样consumer driver在probe的时候，会自动调用pinctrl subsystem提供的API，获取一个default state，并使其生效。

当然，本文所描述的pinctrl driver只算一个简单的demo（只有uart5有关的管脚），实际的项目开发过程中要比这复杂的多，但万变不离其宗，仅仅是代码量和编程技巧的差异而已。

## 5. 参考文档

[1] [Linux设备模型(8)\_platform设备](/device_model/platform_device.html)

[2] [Documentation/pinctrl.txt](https://github.com/wowotechX/linux/blob/x_integration/Documentation/pinctrl.txt)

[3] [linux内核中的GPIO系统之（4）：pinctrl驱动的理解和结](/gpio_subsystem/pinctrl-driver-summary.html)

[4] [https://github.com/96boards/documentation/blob/master/ConsumerEdition/Bubblegum-96/HardwareDocs/SoC\_bubblegum96.pdf](https://github.com/96boards/documentation/blob/master/ConsumerEdition/Bubblegum-96/HardwareDocs/SoC_bubblegum96.pdf "https://github.com/96boards/documentation/blob/master/ConsumerEdition/Bubblegum-96/HardwareDocs/SoC_bubblegum96.pdf")

[5] [https://github.com/96boards/documentation/blob/master/ConsumerEdition/Bubblegum-96/HardwareDocs/Schematics\_Bubblegum96.pdf](https://github.com/96boards/documentation/blob/master/ConsumerEdition/Bubblegum-96/HardwareDocs/Schematics_Bubblegum96.pdf "https://github.com/96boards/documentation/blob/master/ConsumerEdition/Bubblegum-96/HardwareDocs/Schematics_Bubblegum96.pdf")

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/x_project/kernel_pinctrl_driver_porting.html)。

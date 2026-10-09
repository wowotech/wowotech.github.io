---
title: "Linux common clock framework(2)_clock provider"
date: 2014-10-23T23:49:18+08:00
url: "/pm_subsystem/clock_provider.html"
gid: "102"
emlog_type: "blog"
summary: "本文接 上篇文章 ，从clock driver的角度，分析怎么借助common clock framework管理系统的时钟资源。换句话说，就是怎么编写一个clock driver。 由于kernel称clock driver为clock provider（相应的，clock的使用者为clock consumer），因此本文遵循这个规则，统一以clock provider命名。"
author: "wowo"
category: "电源管理子系统"
category_alias: "pm_subsystem"
tags: ["Linux", "framework", "clock", "provider", "dts"]
views: 52866
comment_count: 33
aliases:
  - "/pm_subsystem/102.html"
  - "/102.html"
---

#### 1. 前言

本文接[上篇文章](/pm_subsystem/clk_overview.html)，从clock driver的角度，分析怎么借助common clock framework管理系统的时钟资源。换句话说，就是怎么编写一个clock driver。

由于kernel称clock driver为clock provider（相应的，clock的使用者为clock consumer），因此本文遵循这个规则，统一以clock provider命名。

#### 2. clock有关的DTS

我们在“[Linux common clock framework(1)\_概述](/pm_subsystem/clk_overview.html)”中讲述clock consumer怎么使用clock时，提到过clock consumer怎么在DTS中指定所使用的clock。这里再做进一步说明。

##### 2.1 clock provider的DTS

我们知道，DTS（Device Tree Source）是用来描述设备信息的，那系统的clock资源，是什么设备呢？换句话，用什么设备表示呢？这决定了clock provider的DTS怎么写。

通常有两种方式：

方式1，将系统所有的clock，抽象为一个虚拟的设备，用一个DTS node表示。这个虚拟的设备称作clock controller，参考如下例子：

```
   1: /* arch/arm/boot/dts/exynos4210.dtsi */
```

```
   2: clock: clock-controller@0x10030000 {
```

```
   3:         compatible = "samsung,exynos4210-clock";
```

```
   4:         reg = <0x10030000 0x20000>;
```

```
   5:         #clock-cells = <1>;
```

```
   6: };
```

> clock，该clock设备的名称，clock consumer可以根据该名称引用clock；
>
> #clock-cells，该clock的cells，1表示该clock有多个输出，clock consumer需要通过ID值指定所要使用的clock（很好理解，系统那么多clock，被抽象为1个设备，因而需要额外的ID标识）。

方式2，每一个可输出clock的器件，如“[Linux common clock framework(1)\_概述](/pm_subsystem/clk_overview.html)”所提及的Oscillator、PLL、Mux等等，都是一个设备，用一个DTS node表示。每一个器件，即是clock provider，也是clock consumer（根节点除外，如OSC），因为它需要接受clock输入，经过处理后，输出clock。参考如下例子（如果能拿到对应的datasheet会更容易理解）：

```
   1: /* arch/arm/boot/dts/sun4i-a10.dtsi */
```

```
   2: clocks {
```

```
   3:     #address-cells = <1>;
```

```
   4:     #size-cells = <1>;
```

```
   5:     ranges;
```

```
   6:  
```

```
   7:     /*
```

```
   8:      * This is a dummy clock, to be used as placeholder on
```

```
   9:      * other mux clocks when a specific parent clock is not
```

```
  10:      * yet implemented. It should be dropped when the driver
```

```
  11:      * is complete.
```

```
  12:      */
```

```
  13:     dummy: dummy {
```

```
  14:         #clock-cells = <0>;
```

```
  15:         compatible = "fixed-clock";
```

```
  16:         clock-frequency = <0>;
```

```
  17:     };
```

```
  18:  
```

```
  19:     osc24M: osc24M@01c20050 {
```

```
  20:         #clock-cells = <0>;
```

```
  21:         compatible = "allwinner,sun4i-osc-clk";
```

```
  22:         reg = <0x01c20050 0x4>;
```

```
  23:         clock-frequency = <24000000>;
```

```
  24:     };
```

```
  25:  
```

```
  26:     osc32k: osc32k {
```

```
  27:         #clock-cells = <0>;
```

```
  28:         compatible = "fixed-clock";
```

```
  29:         clock-frequency = <32768>;
```

```
  30:     };
```

```
  31:  
```

```
  32:     pll1: pll1@01c20000 {
```

```
  33:         #clock-cells = <0>;
```

```
  34:         compatible = "allwinner,sun4i-pll1-clk";
```

```
  35:         reg = <0x01c20000 0x4>;
```

```
  36:         clocks = <&osc24M>;
```

```
  37:     };
```

```
  38:  
```

```
  39:     /* dummy is 200M */
```

```
  40:     cpu: cpu@01c20054 {
```

```
  41:         #clock-cells = <0>;
```

```
  42:         compatible = "allwinner,sun4i-cpu-clk";
```

```
  43:         reg = <0x01c20054 0x4>;
```

```
  44:         clocks = <&osc32k>, <&osc24M>, <&pll1>, <&dummy>;
```

```
  45:     };
```

```
  46:  
```

```
  47:     axi: axi@01c20054 {
```

```
  48:         #clock-cells = <0>;
```

```
  49:         compatible = "allwinner,sun4i-axi-clk";
```

```
  50:         reg = <0x01c20054 0x4>;
```

```
  51:         clocks = <&cpu>;
```

```
  52:     };
```

```
  53:  
```

```
  54:     axi_gates: axi_gates@01c2005c {
```

```
  55:         #clock-cells = <1>;
```

```
  56:         compatible = "allwinner,sun4i-axi-gates-clk";
```

```
  57:         reg = <0x01c2005c 0x4>;
```

```
  58:         clocks = <&axi>;
```

```
  59:         clock-output-names = "axi_dram";
```

```
  60:     };
```

```
  61:  
```

```
  62:     ahb: ahb@01c20054 {
```

```
  63:         #clock-cells = <0>;
```

```
  64:         compatible = "allwinner,sun4i-ahb-clk";
```

```
  65:         reg = <0x01c20054 0x4>;
```

```
  66:         clocks = <&axi>;
```

```
  67:     };
```

```
  68:  
```

```
  69:     ahb_gates: ahb_gates@01c20060 {
```

```
  70:         #clock-cells = <1>;
```

```
  71:         compatible = "allwinner,sun4i-ahb-gates-clk";
```

```
  72:         reg = <0x01c20060 0x8>;
```

```
  73:         clocks = <&ahb>;
```

```
  74:         clock-output-names = "ahb_usb0", "ahb_ehci0",
```

```
  75:             "ahb_ohci0", "ahb_ehci1", "ahb_ohci1", "ahb_ss",
```

```
  76:             "ahb_dma", "ahb_bist", "ahb_mmc0", "ahb_mmc1",
```

```
  77:             "ahb_mmc2", "ahb_mmc3", "ahb_ms", "ahb_nand",
```

```
  78:             "ahb_sdram", "ahb_ace",    "ahb_emac", "ahb_ts",
```

```
  79:             "ahb_spi0", "ahb_spi1", "ahb_spi2", "ahb_spi3",
```

```
  80:             "ahb_pata", "ahb_sata", "ahb_gps", "ahb_ve",
```

```
  81:             "ahb_tvd", "ahb_tve0", "ahb_tve1", "ahb_lcd0",
```

```
  82:             "ahb_lcd1", "ahb_csi0", "ahb_csi1", "ahb_hdmi",
```

```
  83:             "ahb_de_be0", "ahb_de_be1", "ahb_de_fe0",
```

```
  84:             "ahb_de_fe1", "ahb_mp", "ahb_mali400";
```

```
  85:     };
```

```
  86:  
```

```
  87:     apb0: apb0@01c20054 {
```

```
  88:         #clock-cells = <0>;
```

```
  89:         compatible = "allwinner,sun4i-apb0-clk";
```

```
  90:         reg = <0x01c20054 0x4>;
```

```
  91:         clocks = <&ahb>;
```

```
  92:     };
```

```
  93:  
```

```
  94:     apb0_gates: apb0_gates@01c20068 {
```

```
  95:         #clock-cells = <1>;
```

```
  96:         compatible = "allwinner,sun4i-apb0-gates-clk";
```

```
  97:         reg = <0x01c20068 0x4>;
```

```
  98:         clocks = <&apb0>;
```

```
  99:         clock-output-names = "apb0_codec", "apb0_spdif",
```

```
 100:             "apb0_ac97", "apb0_iis", "apb0_pio", "apb0_ir0",
```

```
 101:             "apb0_ir1", "apb0_keypad";
```

```
 102:     };
```

```
 103:  
```

```
 104:     /* dummy is pll62 */
```

```
 105:     apb1_mux: apb1_mux@01c20058 {
```

```
 106:         #clock-cells = <0>;
```

```
 107:         compatible = "allwinner,sun4i-apb1-mux-clk";
```

```
 108:         reg = <0x01c20058 0x4>;
```

```
 109:         clocks = <&osc24M>, <&dummy>, <&osc32k>;
```

```
 110:     };
```

```
 111:  
```

```
 112:     apb1: apb1@01c20058 {
```

```
 113:         #clock-cells = <0>;
```

```
 114:         compatible = "allwinner,sun4i-apb1-clk";
```

```
 115:         reg = <0x01c20058 0x4>;
```

```
 116:         clocks = <&apb1_mux>;
```

```
 117:     };
```

```
 118:  
```

```
 119:     apb1_gates: apb1_gates@01c2006c {
```

```
 120:         #clock-cells = <1>;
```

```
 121:         compatible = "allwinner,sun4i-apb1-gates-clk";
```

```
 122:         reg = <0x01c2006c 0x4>;
```

```
 123:         clocks = <&apb1>;
```

```
 124:         clock-output-names = "apb1_i2c0", "apb1_i2c1",
```

```
 125:             "apb1_i2c2", "apb1_can", "apb1_scr",
```

```
 126:             "apb1_ps20", "apb1_ps21", "apb1_uart0",
```

```
 127:             "apb1_uart1", "apb1_uart2", "apb1_uart3",
```

```
 128:             "apb1_uart4", "apb1_uart5", "apb1_uart6",
```

```
 129:             "apb1_uart7";
```

```
 130:     };
```

```
 131: };
```

> osc24M和osc32k是两个root clock，因此只做clock provider功能。它们的cells均为0，因为直接使用名字即可引用。另外，增加了“clock-frequency”自定义关键字，这样在板子使用的OSC频率改变时，如变为12M，不需要重新编译代码，只需更改DTS的频率即可（这不正是Device Tree的核心思想吗！）。话说回来了，osc24M的命名不是很好，如果频率改变，名称也得改吧，clock consumer的引用也得改吧；
>
> pll1即是clock provider（cell为0，直接用名字引用），也是clock consumer（clocks关键字，指定输入clock为“osc24M”）；
>
> 再看一个复杂一点的，ahb\_gates，它是clock provider（cell为1），通过clock-output-names关键字，描述所有的输出时钟。同时它也是clock consumer（由clocks关键字可知输入clock为“ahb”）。需要注意的是，clock-output-names关键字只为了方便clock provider编程方便（后面会讲），clock consumer不能使用（或者可理解为不可见）；

也许您会问，这些DTS描述，怎么使用？怎么和代码关联起来？先不着急，我们慢慢看。

##### 2.2 clock consumer的DTS

在2.1中的方法二，我们已经看到clock consumer的DTS了，因为很多clock provider也是clock consumer。这里再举几个例子，做进一步说明。

例子1（对应2.1中的方式1，来自同一个DTS文件）：

```
   1: /* arch/arm/boot/dts/exynos4210.dtsi */
```

```
   2: mct@10050000 {
```

```
   3:         compatible = "samsung,exynos4210-mct";
```

```
   4:         ...
```

```
   5:         clocks = <&clock 3>, <&clock 344>;
```

```
   6:         clock-names = "fin_pll", "mct";
```

```
   7:         ...
```

```
   8: };
```

> clocks，指明该设备的clock列表，clk\_get时，会以它为关键字，去device\_node中搜索，以得到对应的struct clk指针；
>
> clocks需要指明的信息，由clock provider的“#clock-cells”规定：为0时，只需要提供一个clock provider name（称作phandle）；为1时，表示phandle有多个输出，则需要额外提供一个ID，指明具体需要使用那个输出。这个例子直接用立即数表示，更好的做法是，将系统所有clock的ID，定义在一个头文件中，而DTS可以包含这个头文件，如“clocks = <&clock CLK\_SPI0>”；
>
> clock-names，为clocks指定的那些clock分配一些易于使用的名字，driver可以直接以名字为参数，get clock的句柄（具体可参考“[Linux common clock framework(1)\_概述](/pm_subsystem/clk_overview.html)”中clk\_get相关的接口描述）。

例子2，如果clock provider的“#clock-cells”为0，可直接引用该clock provider的名字，具体可参考2.1中的方式2。

例子3，2.1中方式2有一个clock provider的名字为apb0\_gates，它的“#clock-cells”为1，并通过clock-output-names指定了所有的输出clock，那么，clock consumer怎么引用呢？如下（2和.1中的方式2，来自同一个DTS文件）：

```
   1: /* arch/arm/boot/dts/sun4i-a10.dtsi */
```

```
   2: soc@01c20000 {
```

```
   3:         compatible = "simple-bus";
```

```
   4:         ...
```

```
   5:  
```

```
   6:         pio: pinctrl@01c20800 {
```

```
   7:                 compatible = "allwinner,sun4i-a10-pinctrl";
```

```
   8:                 reg = <0x01c20800 0x400>;
```

```
   9:                 clocks = <&apb0_gates 5>;
```

```
  10:                 ...
```

```
  11:         }
```

```
  12: }
```

> 和例子1一样，指定phandle为“aph0\_gates”，ID为5。

##### 2.3 DTS相关的讨论和总结

我们在上面提到了clock provider的两种DTS定义方式，哪一种好呢？

从规范化、条理性的角度，毫无疑问方式2是好的，它真正理解了Device Tree的精髓，并细致的执行。且可以利用很多clock framework的标准实现（后面会讲）。

而方式1的优点是，DTS容易写，相应的clock driver也较为直观，只是注册一个一个clock provider即可，没有什么逻辑可言。换句话说，方式1比较懒。

后面的API描述，蜗蜗会着重从方式2的角度，因为这样才能体会到软件设计中的美学。

注1：上面例子中用到了两个公司的代码，方式1是三星的，方式2是全志的。说实话，全志的代码写的真漂亮，一个默默无闻的白牌公司，比三星这种国际大公司强多了。从这里，我们可以看到中国科技业的未来，还是很乐观的。

#### 3. clock provider有关的API汇整

clock provider的API位于include/linux/clk\_provider.h。

##### 3.1 struct clk\_hw

由“[Linux common clock framework(1)\_概述](/pm_subsystem/clk_overview.html)”可知，clock framework使用struct clk结构抽象clock，但该结构对clock consumer是透明的（不需要知道它的内部细节）。同样，struct clk对clock provider也是透明的。framework提供了struct clk\_hw结构，从clock provider的角度，描述clock，该结构的定义如下：

```
   1: struct clk_hw {
```

```
   2:         struct clk *clk;
```

```
   3:         const struct clk_init_data *init;
```

```
   4: };
```

> clk，struct clk指针，由clock framework分配并维护，并在需要时提供给clock consumer使用；
>
> init，描述该clock的静态数据，clock provider负责把系统中每个clock的静态数据准备好，然后交给clock framework的核心逻辑，剩下的事情，clock provider就不用操心了。这个过程，就是clock driver的编写过程，简单吧？该静态数据的数据结构如下。

```
   1: struct clk_init_data {
```

```
   2:         const char              *name;
```

```
   3:         const struct clk_ops    *ops;
```

```
   4:         const char              **parent_names;
```

```
   5:         u8                      num_parents;
```

```
   6:         unsigned long           flags;
```

```
   7: };
```

> name，该clock的名称；
>
> ops，该clock相关的操作函数集，具体参考下面的描述；
>
> parent\_names，该clock所有的parent clock的名称。这是一个字符串数组，保存了所有可能的parent；
>
> num\_parents，parent的个数；
>
> flags，一些framework级别的flags，后面会详细说明。

```
   1: struct clk_ops {
```

```
   2:         int             (*prepare)(struct clk_hw *hw);
```

```
   3:         void            (*unprepare)(struct clk_hw *hw);
```

```
   4:         int             (*is_prepared)(struct clk_hw *hw);
```

```
   5:         void            (*unprepare_unused)(struct clk_hw *hw);
```

```
   6:         int             (*enable)(struct clk_hw *hw);
```

```
   7:         void            (*disable)(struct clk_hw *hw);
```

```
   8:         int             (*is_enabled)(struct clk_hw *hw);
```

```
   9:         void            (*disable_unused)(struct clk_hw *hw);
```

```
  10:         unsigned long   (*recalc_rate)(struct clk_hw *hw,
```

```
  11:                                         unsigned long parent_rate);
```

```
  12:         long            (*round_rate)(struct clk_hw *hw, unsigned long,
```

```
  13:                                         unsigned long *);
```

```
  14:         int             (*set_parent)(struct clk_hw *hw, u8 index);
```

```
  15:         u8              (*get_parent)(struct clk_hw *hw);
```

```
  16:         int             (*set_rate)(struct clk_hw *hw, unsigned long,
```

```
  17:                                     unsigned long);
```

```
  18:         void            (*init)(struct clk_hw *hw);
```

```
  19: };
```

> 这是clock的操作函数集， 很多和“[Linux common clock framework(1)\_概述](/pm_subsystem/clk_overview.html)”中的clock framework通用API一致（通用API会直接调用相应的操作函数）：
>
> is\_prepared，判断clock是否已经prepared。可以不提供，clock framework core会维护一个prepare的计数（该计数在clk\_prepare调用时加一，在clk\_unprepare时减一），并依据该计数判断是否prepared；
>
> unprepare\_unused，自动unprepare unused clocks；
>
> is\_enabled，和is\_prepared类似；
>
> disable\_unused，自动disable unused clocks；
>
> 注2：clock framework core提供一个clk\_disable\_unused接口，在系统初始化的late\_call中调用，用于关闭unused clocks，这个接口会调用相应clock的.unprepare\_unused和.disable\_unused函数。
>
> recalc\_rate，以parent clock rate为参数，从新计算并返回clock rate；
>
> 注3：细心的读者可能会发现，该结构没有提供get\_rate函数，因为会有一个rate变量缓存，另外可以使用recalc\_rate。
>
> round\_rate，该接口有点特别，在返回rounded rate的同时，会通过一个指针，返回round后parent的rate。这和CLK\_SET\_RATE\_PARENT flag有关，后面会详细解释；
>
> init，clock的初始化接口，会在clock被register到内核时调用。

```
   1: /*
```

```
   2:  * flags used across common struct clk.  these flags should only affect the
```

```
   3:  * top-level framework.  custom flags for dealing with hardware specifics
```

```
   4:  * belong in struct clk_foo
```

```
   5:  */
```

```
   6: #define CLK_SET_RATE_GATE       BIT(0) /* must be gated across rate change */
```

```
   7: #define CLK_SET_PARENT_GATE     BIT(1) /* must be gated across re-parent */
```

```
   8: #define CLK_SET_RATE_PARENT     BIT(2) /* propagate rate change up one level */
```

```
   9: #define CLK_IGNORE_UNUSED       BIT(3) /* do not gate even if unused */
```

```
  10: #define CLK_IS_ROOT             BIT(4) /* root clk, has no parent */
```

```
  11: #define CLK_IS_BASIC            BIT(5) /* Basic clk, can't do a to_clk_foo() */
```

```
  12: #define CLK_GET_RATE_NOCACHE    BIT(6) /* do not use the cached clk rate */
```

> 上面是framework级别的flags，可以使用或的关系，指定多个flags，解释如下：
>
> CLK\_SET\_RATE\_GATE，表示在改变该clock的rate时，必须gated（关闭）；
>   
> CLK\_SET\_PARENT\_GATE，表示在改变该clock的parent时，必须gated（关闭）；
>   
> CLK\_SET\_RATE\_PARENT，表示改变该clock的rate时，要将该改变传递到上层parent（下面再详细说明）；
>   
> CLK\_IGNORE\_UNUSED，忽略disable unused的调用；
>   
> CLK\_IS\_ROOT，该clock为root clock，没有parent；
>   
> CLK\_IS\_BASIC，不再使用了；
>   
> CLK\_GET\_RATE\_NOCACHE，get rate时，不要从缓存中拿，而是从新计算。

注4：round\_rate和CLK\_SET\_RATE\_PARENT
  
当clock consumer调用clk\_round\_rate获取一个近似的rate时，如果该clock没有提供.round\_rate函数，有两种方法：
  
1）在没有设置CLK\_SET\_RATE\_PARENT标志时，直接返回该clock的cache rate
  
2）如果设置了CLK\_SET\_RATE\_PARENT标志，则会询问parent，即调用clk\_round\_rate获取parent clock能提供的、最接近该rate的值。这是什么意思呢？也就是说，如果parent clock可以得到一个近似的rate值，那么通过改变parent clock，就能得到所需的clock。
  
在后续的clk\_set\_rate接口中，会再次使用该flag，如果置位，则会在设置rate时，传递到parent clock，因此parent clock的rate可能会重设。
  
讲的很拗口，我觉得我也没说清楚，那么最好的方案就是：在写clock driver时，最好不用这个flag，简单的就是最好的（前提是能满足需求）。

##### 3.2 clock tree建立相关的API

**3.2.1 clk\_register**

系统中，每一个clock都有一个struct clk\_hw变量描述，clock provider需要使用register相关的接口，将这些clock注册到kernel，clock framework的核心代码会把它们转换为struct clk变量，并以tree的形式组织起来。这些接口的原型如下：

```
   1: /**
```

```
   2:  * clk_register - allocate a new clock, register it and return an opaque cookie
```

```
   3:  * @dev: device that is registering this clock
```

```
   4:  * @hw: link to hardware-specific clock data
```

```
   5:  *
```

```
   6:  * clk_register is the primary interface for populating the clock tree with new
```

```
   7:  * clock nodes.  It returns a pointer to the newly allocated struct clk which
```

```
   8:  * cannot be dereferenced by driver code but may be used in conjuction with the
```

```
   9:  * rest of the clock API.  In the event of an error clk_register will return an
```

```
  10:  * error code; drivers must test for an error code after calling clk_register.
```

```
  11:  */
```

```
  12: struct clk *clk_register(struct device *dev, struct clk_hw *hw);
```

```
  13: struct clk *devm_clk_register(struct device *dev, struct clk_hw *hw);
```

```
  14:  
```

```
  15: void clk_unregister(struct clk *clk);
```

```
  16: void devm_clk_unregister(struct device *dev, struct clk *clk);
```

> 这些API比较简单（复杂的是怎么填充struct clk\_hw变量），register接口接受一个填充好的struct clk\_hw指针，将它转换为sruct clk结构，并根据parent的名字，添加到clock tree中。

不过，clock framework所做的远比这周到，它基于clk\_register，又封装了其它接口，使clock provider在注册clock时，连struct clk\_hw都不需要关心，而是直接使用类似人类语言的方式，下面继续。

**3.2.2 clock分类及register**

根据clock的特点，clock framework将clock分为fixed rate、gate、devider、mux、fixed factor、composite六类，每一类clock都有相似的功能、相似的控制方式，因而可以使用相同的逻辑s，统一处理，这充分体现了面向对象的思想。

1）fixed rate clock

这一类clock具有固定的频率，不能开关、不能调整频率、不能选择parent、不需要提供任何的clk\_ops回调函数，是最简单的一类clock。

可以直接通过DTS配置的方式支持，clock framework core能直接从DTS中解出clock信息，并自动注册到kernel，不需要任何driver支持。

clock framework使用struct clk\_fixed\_rate结构抽象这一类clock，另外提供了一个接口，可以直接注册fixed rate clock，如下：

```
   1: /**
```

```
   2:  * struct clk_fixed_rate - fixed-rate clock
```

```
   3:  * @hw:         handle between common and hardware-specific interfaces
```

```
   4:  * @fixed_rate: constant frequency of clock
```

```
   5:  */
```

```
   6: struct clk_fixed_rate {
```

```
   7:         struct          clk_hw hw;
```

```
   8:         unsigned long   fixed_rate;
```

```
   9:         u8              flags;
```

```
  10: };
```

```
  11:  
```

```
  12: extern const struct clk_ops clk_fixed_rate_ops;
```

```
  13: struct clk *clk_register_fixed_rate(struct device *dev, const char *name,
```

```
  14:                 const char *parent_name, unsigned long flags,
```

```
  15:                 unsigned long fixed_rate);
```

> clock provider一般不需要直接使用struct clk\_fixed\_rate结构，因为clk\_register\_fixed\_rate接口是非常方便的；
>
> clk\_register\_fixed\_rate接口以clock name、parent name、fixed\_rate为参数，创建一个具有固定频率的clock，该clock的clk\_ops也是clock framework提供的，不需要provider关心；
>
> 如果使用DTS的话，clk\_register\_fixed\_rate都不需要，直接在DTS中配置即可，后面会说明。

2）gate clock

这一类clock只可开关（会提供.enable/.disable回调），可使用下面接口注册：

```
   1: struct clk *clk_register_gate(struct device *dev, const char *name,
```

```
   2:                 const char *parent_name, unsigned long flags,
```

```
   3:                 void __iomem *reg, u8 bit_idx,
```

```
   4:                 u8 clk_gate_flags, spinlock_t *lock);
```

> 需要提供的参数包括：
>
> name，clock的名称；
>
> parent\_name，parent clock的名称，没有的话可留空；
>
> flags，可参考3.1中的说明；
>
> reg，控制该clock开关的寄存器地址（虚拟地址）；
>
> bit\_idx，控制clock开关的bit位（是1开，还是0开，可通过下面gate特有的flag指定）；
>
> clk\_gate\_flags，gate clock特有的flag，当前只有一种：CLK\_GATE\_SET\_TO\_DISABLE，clock开关控制的方式，如果置位，表示写1关闭clock，反之亦然；
>
> lock，如果clock开关时需要互斥，可提供一个spinlock。

3）divider clock

这一类clock可以设置分频值（因而会提供.recalc\_rate/.set\_rate/.round\_rate回调），可通过下面两个接口注册：

```
   1: struct clk *clk_register_divider(struct device *dev, const char *name,
```

```
   2:                 const char *parent_name, unsigned long flags,
```

```
   3:                 void __iomem *reg, u8 shift, u8 width,
```

```
   4:                 u8 clk_divider_flags, spinlock_t *lock);
```

> 该接口用于注册分频比规则的clock：
>
> reg，控制clock分频比的寄存器；
>
> shift，控制分频比的bit在寄存器中的偏移；
>
> width，控制分频比的bit位数，默认情况下，实际的divider值是寄存器值加1。如果有其它例外，可使用下面的的flag指示；
>
> clk\_divider\_flags，divider clock特有的flag，包括：
>
> CLK\_DIVIDER\_ONE\_BASED，实际的divider值就是寄存器值（0是无效的，除非设置CLK\_DIVIDER\_ALLOW\_ZERO flag）；
>   
>  CLK\_DIVIDER\_POWER\_OF\_TWO，实际的divider值是寄存器值得2次方；
>   
>  CLK\_DIVIDER\_ALLOW\_ZERO，divider值可以为0（不改变，视硬件支持而定）。
>
> 如有需要其他分频方式，就需要使用另外一个接口，如下：

```
   1: struct clk *clk_register_divider_table(struct device *dev, const char *name,
```

```
   2:                 const char *parent_name, unsigned long flags,
```

```
   3:                 void __iomem *reg, u8 shift, u8 width,
```

```
   4:                 u8 clk_divider_flags, const struct clk_div_table *table,
```

```
   5:                 spinlock_t *lock);
```

> 该接口用于注册分频比不规则的clock，和上面接口比较，差别在于divider值和寄存器值得对应关系由一个table决定，该table的原型为：
>
> struct clk\_div\_table {
>   
>  unsigned int val;
>   
>  unsigned int div;
>   
> };
>
> 其中val表示寄存器值，div表示分频值，它们的关系也可以通过clk\_divider\_flags改变。

4）mux clock

这一类clock可以选择多个parent，因为会实现.get\_parent/.set\_parent/.recalc\_rate回调，可通过下面两个接口注册：

```
   1: struct clk *clk_register_mux(struct device *dev, const char *name,
```

```
   2:                 const char **parent_names, u8 num_parents, unsigned long flags,
```

```
   3:                 void __iomem *reg, u8 shift, u8 width,
```

```
   4:                 u8 clk_mux_flags, spinlock_t *lock);
```

> 该接口可注册mux控制比较规则的clock（类似divider clock）：
>
> parent\_names，一个字符串数组，用于描述所有可能的parent clock；
>
> num\_parents，parent clock的个数；
>
> reg、shift、width，选择parent的寄存器、偏移、宽度，默认情况下，寄存器值为0时，对应第一个parent，依此类推。如有例外，可通过下面的flags，以及另外一个接口实现；
>
> clk\_mux\_flags，mux clock特有的flag：
>
> CLK\_MUX\_INDEX\_ONE，寄存器值不是从0开始，而是从1开始；
>   
>  CLK\_MUX\_INDEX\_BIT，寄存器值为2的幂。

```
   1: struct clk *clk_register_mux_table(struct device *dev, const char *name,
```

```
   2:                 const char **parent_names, u8 num_parents, unsigned long flags,
```

```
   3:                 void __iomem *reg, u8 shift, u32 mask,
```

```
   4:                 u8 clk_mux_flags, u32 *table, spinlock_t *lock);
```

> 该接口通过一个table，注册mux控制不规则的clock，原理和divider clock类似，不再详细介绍。

5）fixed factor clock

这一类clock具有固定的factor（即multiplier和divider），clock的频率是由parent clock的频率，乘以mul，除以div，多用于一些具有固定分频系数的clock。由于parent clock的频率可以改变，因而fix factor clock也可该改变频率，因此也会提供.recalc\_rate/.set\_rate/.round\_rate等回调。

可通过下面接口注册：

```
   1: struct clk *clk_register_fixed_factor(struct device *dev, const char *name,
```

```
   2:                 const char *parent_name, unsigned long flags,
```

```
   3:                 unsigned int mult, unsigned int div);
```

另外，这一类接口和fixed rateclock类似，不需要提供driver，只需要配置dts即可。

6）composite clock

顾名思义，就是mux、divider、gate等clock的组合，可通过下面接口注册：

```
   1: struct clk *clk_register_composite(struct device *dev, const char *name,
```

```
   2:                 const char **parent_names, int num_parents,
```

```
   3:                 struct clk_hw *mux_hw, const struct clk_ops *mux_ops,
```

```
   4:                 struct clk_hw *rate_hw, const struct clk_ops *rate_ops,
```

```
   5:                 struct clk_hw *gate_hw, const struct clk_ops *gate_ops,
```

```
   6:                 unsigned long flags);
```

> 看着有点复杂，但理解了上面1~5类clock，这里就只剩下苦力了，耐心一点，就可以了。

**3.2.3 DTS相关的API**

再回到第2章DTS相关的介绍，clock driver使用一个DTS node描述一个clock provider，而clock consumer则会使用类似“clocks = <&clock 32>, <&clock 45>;”的形式引用，clock framework会自行把这些抽象的数字转换成实际的struct clk结构，怎么做的呢？肯定离不开clock provider的帮助。

3.2.1和3.2.2小节所描述的regitser接口，负责把clocks抽象为一个一个的struct clock，与此同时，clock provider需要把这些struct clk结构保存起来，并调用clock framework的接口，将这些对应信息告知framework的OF模块，这样才可以帮助将clock consumer的DTS描述转换为struct clk结构。该接口如下：

```
   1: int of_clk_add_provider(struct device_node *np,
```

```
   2:                         struct clk *(*clk_src_get)(struct of_phandle_args *args,
```

```
   3:                                                    void *data),
```

```
   4:                         void *data);
```

> np，device\_node指针，clock provider在和自己的DTS匹配时获得；
>
> clk\_src\_get，获取struct clk指针的回调函数，由clock provider根据实际的逻辑实现，参数说明如下：
>
> args，struct of\_phandle\_args类型的指针，由DTS在解析参数时传递。例如上面的“clocks = <&clock 32>, <&clock 45>;”，32、45就是通过这个指针传进来的；
>
> data，保存struct clk结构的指针，通常是一个数组，具体由provider决定。
>
> data，和回调函数中的data意义相同，只是这里由provider提供，get时由clock framework core传递给回调函数。

对于常用的one cell clock provider（第2章的例子），clock framework core提供一个默认的会调用函数，如下：

```
   1: struct clk_onecell_data {
```

```
   2:         struct clk **clks;
```

```
   3:         unsigned int clk_num;
```

```
   4: };
```

```
   5: struct clk *of_clk_src_onecell_get(struct of_phandle_args *clkspec, void *data);
```

> 其中data指针为struct clk\_onecell\_data结构，该结构提供了clk指针和clk\_num的对应，clock provider在regitser clocks时，同时维护一个clk和num对应的数组，并调用of\_clk\_add\_provider接口告知clock framework core即可。

#### 4. 使用clock framework编写clock驱动的步骤

编写clock driver的步骤大概如下：

1）分析硬件的clock tree，按照上面所描述的分类，讲这些clock分类。

2）将clock tree在DTS中描述出来，需要注意以下几2点：

a）对于fixed rate clocks，.compatible固定填充"fixed-clock"，并提供"clock-frequency"和"clock-output-names"关键字。之后不需要再driver中做任何处理，clock framework core会帮我们搞定一切。

b）同样，对于fixed factor clock，.compatible为"fixed-factor-clock"，并提供"clock-div"、"clock-mult"和"clock-output-names"关键字。clock framework core会帮我们搞定一切。

切记，尽量利用kernel已有资源，不要多写一行代码，简洁的就是美的！

3）对于不能由clock framework core处理的clock，需要在driver中使用struct of\_device\_id进行匹配，并在初始化时，调用OF模块，查找所有的DTS匹配项，并执行合适的regitser接口，注册clock。

4）注册clock的同时，将返回的struct clk指针，保存在一个数组中，并调用of\_clk\_add\_provider接口，告知clock framework core。

5）最后，也是最重要的一点，多看kernel源代码，多模仿，多抄几遍，什么都熟悉了！

*原创文章，转发请注明出处。蜗窝科技*，[www.wowotech.net](/pm_subsystem/clock_provider.html)。

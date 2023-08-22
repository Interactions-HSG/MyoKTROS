library(ggplot2)

pdf.options(reset = TRUE, onefile = TRUE, width = 8, height = 8)
pdf(file="test.pdf")

# The palette with gray:
cbPalette <- c("#999999", "#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7")

res = read.csv('./engine_bench_100subs.csv')
res <- within(res, ri <- 1 / ns * 1e+09)

ggplot(data = res, aes(x=nTag, y=ri, colour=factor(engine,labels=c("Legacy","Linear Search","Patricia Trie","Splay Tree")), shape=factor(engine,labels=c("Legacy","Linear Search","Patricia Trie","Splay Tree")), linetype = factor(engine,labels=c("Legacy","Linear Search","Patricia Trie","Splay Tree")))) +
    geom_point(size=6) +
    geom_line() +
    labs(x=expression(Nu[E]), y=expression(R[i]), shape="engine", colour="engine", linetype="engine") +
    theme_classic() +
    scale_x_continuous(breaks=seq(0, 1000, 200)) +
    #scale_y_continuous(breaks=c(0, 3, 30 ,300 , 3000), trans = 'log10') +
    #scale_y_continuous() +
    scale_color_manual(values=c('#CC79A7','#0072B2','#D55E00','#009E73')) +
    scale_shape_manual(values=c(15, 12, 13, 14)) +
    scale_linetype_manual(values=c(6, 1, 5, 3)) +
    theme(legend.position = "none",
          text=element_text(size=26))

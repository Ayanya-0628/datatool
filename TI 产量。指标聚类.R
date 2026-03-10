# =======================================================
# 0. 加载必要的包
# =======================================================
library(readxl)
library(ggplot2)
library(ggtree)
library(dplyr)
library(ape)
library(viridis)

# --- 关键修改 1：正确配置中文字体 ---
library(showtext)
showtext_auto() 

# 这里的 "simhei.ttf" 是Windows自带的黑体文件
# 如果报错找不到字体，请把 "simhei.ttf" 改为 "msyh.ttf" (微软雅黑)
font_add("SimHei", "simhei.ttf") 

# =======================================================
# 1. 数据读取与处理
# =======================================================
file_path <- "C:/Users/张银/Desktop/毕业排序/24 Ti画图.xlsx"
df_raw <- read_excel(file_path)
df_work <- as.data.frame(df_raw)

# --- 处理行名 ---
raw_names <- as.character(df_work[, 1])
if(any(duplicated(raw_names))){
  combo_names <- make.unique(raw_names)
} else {
  combo_names <- raw_names
}

# 去掉多余的点，替换为空格
combo_names <- gsub("\\.+", " ", combo_names) 
rownames(df_work) <- combo_names

# --- 筛选指标 ---
target_cols <- c("产量", "糙米率", "消减值", "整精米率", "糊化温度", "蛋白质含量", "直链淀粉含量")

df_cluster <- df_work[, target_cols]
df_cluster <- df_cluster %>% select_if(is.numeric)

# =======================================================
# 2. 聚类分析
# =======================================================
dist_mat <- dist(df_cluster, method = "euclidean")
hc <- hclust(dist_mat, method = "ward.D2")
clus_group <- cutree(hc, k = 3)
group_list <- split(names(clus_group), clus_group)
tree <- as.phylo(hc)
tree_grouped <- groupOTU(tree, group_list)

# =======================================================
# 3. 绘图
# =======================================================

# (1) 基础树图
p <- ggtree(tree_grouped, layout = "circular", aes(color = group), size = 0.8) +
  scale_color_manual(values = c("black", "#E41A1C", "#4DAF4A", "#377EB8"), 
                     name = "聚类分组",
                     labels = c("骨架", "第一类", "第二类", "第三类")) +
  
  # 👇👇👇 修改这里：加大第一个数字 (X轴坐标) 👇👇👇
  # 1.35 表示移动到画布宽度的 135% 处。如果还不够，就改成 1.45
  theme(legend.position = c(1.45, 0.5), 
        text = element_text(family = "SimHei"))

# (2) 添加热图
p_heatmap <- gheatmap(p, 
                      data = df_cluster,   
                      offset = 0,          
                      width = 1.8,         
                      colnames = TRUE,     
                      colnames_position = "top", 
                      colnames_angle = 90, 
                      colnames_offset_y = 3, 
                      font.size = 4.5,     # 字体大小
                      hjust = 0.6,
                      family = "SimHei") + # --- 关键修改 3：热图指标字体 ---
  scale_fill_gradient2(low = "blue", mid = "white", high = "red", 
                       midpoint = 0.5, name = "")

# (3) 添加最外层标签
p_final <- p_heatmap + 
  geom_tiplab(aes(label = label), 
              size = 4.5,            
              offset = 5.3,        
              linesize = 0.4,      
              linetype = "dotted", 
              color = "black",
              family = "SimHei") + # --- 关键修改 4：最外层标签字体 ---
  
  hexpand(.3) + 
  
  labs(title = "") +
  theme(
    plot.title = element_text(hjust = 0.5, size = 16, family = "SimHei"), # 标题字体
    plot.margin = margin(t=30, r=400, b=30, l=30)
  )

# =======================================================
# 4. 保存结果
# =======================================================
print(p_final)

out_dir <- "C:/Users/张银/Desktop/毕业论文数据/24数据"
if(!dir.exists(out_dir)){
  dir.create(out_dir, recursive = TRUE)
}

# 保存图片
png_file <- paste0(out_dir, "/聚类热图_中文修复版.png")
ggsave(png_file, width = 18, height = 18, dpi = 300)

print(paste("处理完成！图片已保存至：", png_file))
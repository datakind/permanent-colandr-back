##Query scripts for evidence based conservation data frame
#Load required libraries and dataframe
library(dplyr)
library(tidyr)
load("~/path-to/evidence_based_7_22.RData")
path <- "~/path-to-working-directory"

##Create set variables for study design, these can be called later when interested in filtering datasets for quality of data
NCS <- filter(data.study, Comps == 0)
EXP <- filter(data.study, Comps == 1, Design.assigned == 1)
OBS <- filter(data.study, Comps == 1, Design.assigned == 0)
EXP_BAC <- filter(data.study, Comps == 1, Design.assigned == 1, Design.control == 0)
OBS_BAC <- filter(data.study, Comps == 1, Design.assigned == 0, Design.control == 0)
EXP_CON <- filter(data.study, Comps == 1, Design.assigned == 1, Design.control == 1)
OBS_CON <- filter(data.study, Comps == 1, Design.assigned == 0, Design.control == 1)
#Summarize counts
study_type_counts <- matrix(nrow=7, ncol=1)
rownames(study_type_counts) <- c("Non-comparative study", "Experimental study", "Observational study", "Experimental before and after study/interrupted time series", "Observational before and after study/interrupted time series", "Experimental with control", "Observational with control")
colnames(study_type_counts) <- c("counts")
#Calculate in for loop and write to blank matrix
study_type_counts[1,1] <- n_distinct(NCS$aid)
study_type_counts[2,1] <- n_distinct(EXP$aid)
study_type_counts[3,1] <- n_distinct(OBS$aid)
study_type_counts[4,1] <- n_distinct(EXP_BAC$aid)
study_type_counts[5,1] <- n_distinct(OBS_BAC$aid)
study_type_counts[6,1] <- n_distinct(EXP_CON$aid)
study_type_counts[7,1] <- n_distinct(OBS_CON$aid)
#Remove rownames and reformat data types
study_type_counts <- as.data.frame(study_type_counts)
stcounts <- as.numeric(study_type_counts$counts)
st_labels <- c("Non-comparative study", "Experimental study", "Observational study", "Experimental before and after study/interrupted time series", "Observational before and after study/interrupted time series", "Experimental with control", "Observational with control")
#Plot barplot
pdf(file="Summary_study_type.pdf")
par(mar = c(7, 4, 2, 2) + 0.2)
end_points = 0.5 + nrow(study_type_counts) + nrow(study_type_counts)-1
barplot(stcounts, main="Study type", axes=TRUE, ylim = c(0,10+max(stcounts)), ylab = "Number of studies", xlab = "", col="purple", angle=45, border=NA, space=1)
text(seq(1.5,end_points,by=2), par("usr")[3]-0.25, srt=60, adj=1.1, xpd=TRUE, labels = paste(st_labels), cex=0.65)
box()
dev.off()

##Plot countries
country_file <- "country_list.csv"
country_list <- paste(path,country_file, sep="")
#load in full country list
country <- read.csv(country_list, head=TRUE, sep=",")
names(country)<- c("Study_country", "Long", "Lat")
#Count number of studies for each country and input into blank data matrix
country_counts <- matrix(nrow=95, ncol=3)
rownames(country_counts) <- country$Study_country
colnames(country_counts) <- c("Study_country", "counts", "counts_for_map")
#Calculate in for loop and write to blank matrix
for (c in country$Study_country){
  subset <- filter(data.study, Study_country == c)
  country_counts[c,1] <- c
  country_counts[c,2] <- n_distinct(subset$aid)
  country_counts[c,3] <- (n_distinct(subset$aid))^2
}
#Remove rownames and reformat data types
rownames(country_counts) = NULL
country_counts <- as.data.frame(country_counts)
#Combine with lat, long, convert data types
final_country <- left_join(country, country_counts, by="Study_country")
ccounts <- as.numeric(as.vector(final_country$counts_for_map))
clabels <- final_country$Study_country
#Load required libraries
library(ggplot2)
library(maps)
#Map points and write to PDF
pdf(file="Country_distribution_map.pdf")
mdat <- map_data('world')
ggplot() + 
  geom_polygon(dat=mdat, aes(long, lat, group=group), fill="grey50") +
  geom_point(data=final_country, aes(x = Lat, y = Long, size=as.numeric(as.vector(counts))), alpha = .5, color="turquoise1")
dev.off()
#scale_size_area(breaks = c(1,10,50,88), labels = c("1", "< 10", "< 50", "< 100"), name = "Number of studies")
#Plot distribution to PDF
pdf(file="Country_distribution.pdf")
par(mar = c(10,10) + 0.2)
end_point1 = 0.5 + nrow(final_country) + nrow(final_country)-1
barplot(ccounts, main="Distribution of studies for non-OECD countries", axes=TRUE, ylim = c(0,5+max(ccounts)), ylab = "Number of studies", xlab = "", col="turquoise", angle=45, border=NA, space=1)
text(seq(1.5,end_point1,by=2), par("usr")[3]-0.25, srt=60, adj=1, xpd=TRUE, labels = paste(clabels), cex=0.65)
box()
dev.off()

##Plot summaries 
##Summarize biomes
biome_cat <- c("T_TSTMBF", "T_TSTDBF", "T_TSTCF", "T_TBMF", "T_TCF", "T_BFT", "T_TSTGSS", "T_TGSS", "T_FGS", "T_MGS", "T_T", "T_MFWS", "T_DXS", "T_M", "FW_LL", "FW_SL", "FW_LR", "FW_LRH", "FW_LRD", "FW_SR", "FW_XB", "M_P", "M_TSS", "M_TU", "M_TRU", "M_TRC", "M_TSTSS")
#Create blank data matrix with labeled rows and columns
biome_counts <- matrix(nrow=27, ncol=2)
rownames(biome_counts) <- biome_cat
colnames(biome_counts) <- c("biome", "counts")
#Calculate number of unique studies for each linkage cell between intervention and outcome
#Calculate in for loop and write to blank matrix
for (b in biome_cat){
  subset <- filter(data.biomes, Biome. == b)
  biome_counts[b,1] <- b
  biome_counts[b,2] <- n_distinct(subset$aid)
  }
#Remove rownames and reformat data types
rownames(biome_counts) <- NULL
biome_counts <- as.data.frame(biome_counts)
bcounts <- as.numeric(biome_counts$counts)
#Create barplot
biome_labels <- c("Tropical/sub-tropical moist broadleaf forests", "Tropical/sub-tropical dry broadleaf forests", "Tropical/sub-tropical coniferous forests", "Temperate broadleaf and mixed forests", "Temperate coniferous forests", "Boreal forests & taiga", "Tropical/sub-tropical grasslands, savannas & shrublands", "Temperate grasslands, savannas & shrublands", "Flooded grasslands and savannas", "Montane grasslands & shrublands", "Tundra", "Mediterranean forests, woodlands & scrubs", "Deserts & xeric shrublands", "Mangroves", "Large lakes", "Small lakes", "Large rivers", "Large river headwaters", "Large river deltas", "Small rivers", "Xeric basins", "Marine-polar", "Marine-temperate shelfs and seas", "Marine-temperate upwelling", "Marine-tropical upwelling", "Marine-tropical corals", "Marine-tropical shelfs and seas")
pdf(file="Summary_biomes.pdf")
par(mar = c(7, 4, 2, 2) + 0.2)
end_point = 0.5 + nrow(biome_counts) + nrow(biome_counts)-1
barplot(bcounts, main="Studies by biome", axes=TRUE, ylim = c(0,5+max(bcounts)), ylab = "Number of studies", xlab = "", col="turquoise", angle=45, border=NA, space=1)
text(seq(1.5,end_point,by=2), par("usr")[3]-0.25, srt=60, adj=1, xpd=TRUE, labels = paste(biome_labels), cex=0.65)
box()
dev.off()

##Summarize Bibliographic information
##Publication type
pub_cat <- c("Peer-reviewed published literature", "Conference proceedings", "Book/book chapter", "Unpublished grey literature", "Other")
#Create blank data matrix with labeled rows and columns
pub_counts <- matrix(nrow=5, ncol=1)
rownames(pub_counts) <- pub_cat
colnames(pub_counts) <- c("counts")
#Calculate in for loop and write to blank matrix
for (p in pub_cat){
  subset <- filter(data.biblio, Pub_type == p)
  pub_counts[p,1] <- n_distinct(subset$aid)
}
#Remove rownames and reformat data types
pub_counts <- as.data.frame(pub_counts)
pcounts <- as.numeric(pub_counts$counts)

##Author affiiation
affil_cat <- c("Academic", "Pub_sec", "Res_int", "Cons", "Non_prof", "Priv_sec")
#Create blank data matrix with labeled rows and columns
affil_counts <- matrix(nrow=6, ncol=1)
rownames(affil_counts) <- affil_cat
colnames(affil_counts) <- c("counts")
#Calculate in for loop and write to blank matrix
for (a in affil_cat){
  subset <- filter(data.biblio, Affil_type == a)
  affil_counts[a,1] <- n_distinct(subset$aid)
}
#Remove rownames and reformat data types
affil_counts <- as.data.frame(affil_counts)
acounts <- as.numeric(affil_counts$counts)

##Publications by year
years <- as.character(c(1970:2014))
#Create blank data matrix with labeled rows and columns
year_counts <- matrix(nrow=45, ncol=1)
rownames(year_counts) <- years
colnames(year_counts) <- c("counts")
data.biblio$Pub_year <- as.character(data.biblio$Pub_year)
#Calculate in for loop and write to blank matrix
for (y in years){
  subset <- filter(data.biblio, Pub_year == y)
  year_counts[y,1] <- n_distinct(subset$aid)
}
#Remove rownames and reformat data types
year_counts <- as.data.frame(year_counts)
ycounts <- as.numeric(year_counts$counts)

##Author affiiation
affil_cat <- c("Academic", "Pub_sec", "Res_int", "Cons", "Non_prof", "Priv_sec")
#Create blank data matrix with labeled rows and columns
affil_counts <- matrix(nrow=6, ncol=1)
rownames(affil_counts) <- affil_cat
colnames(affil_counts) <- c("counts")
#Calculate in for loop and write to blank matrix
for (a in affil_cat){
  subset <- filter(data.biblio, Affil_type == a)
  affil_counts[a,1] <- n_distinct(subset$aid)
}
#Remove rownames and reformat data types
affil_counts <- as.data.frame(affil_counts)
acounts <- as.numeric(affil_counts$counts)
affil_labels <- c("Academic", "Public sector", "Research institute", "Consultant", "Non-profit", "Private sector")

#Create barplots in PDFs
end_point = 0.5 + nrow(pub_counts) + nrow(pub_counts)-1
end_point_2 = 0.5 + nrow(affil_counts) + nrow(affil_counts)-1
end_point_3 = 0.5 + nrow(year_counts) + nrow(year_counts)-1
pdf(file="Summary_Bibliographic.pdf")
layout(matrix(c(1,1,2,3), 2, 2, byrow=TRUE))
barplot(ycounts, main="Publications by year", axes=TRUE, ylim = c(0,5+max(ycounts)), ylab = "Number of studies", xlab = "", col="purple", angle=45, border=NA, space=1)
text(seq(1.5,end_point_3,by=2), par("usr")[3]-0.25, srt=60, pos=1, xpd=TRUE, labels = paste(years), cex=0.65)
box()
barplot(pcounts, main="Publication type", axes=TRUE, ylim = c(0,5+max(pcounts)), ylab = "Number of studies", xlab = "", col="purple", border=NA, space=1)
text(seq(1.5,end_point,by=2), par("usr")[3]-0.25, srt=60, adj=1, xpd=TRUE, labels = paste(pub_cat), cex=0.65)
box()
barplot(acounts, main="Affiliation of first author", axes=TRUE, ylim = c(0,5+max(acounts)), ylab = "Number of studies", xlab = "", col="purple", angle=45, border=NA, space=1)
text(seq(1.5,end_point_2,by=2), par("usr")[3]-0.25, srt=60, adj=1, xpd=TRUE, labels = paste(affil_labels), cex=0.65)
box()
dev.off()

##Summarize intervention and outcome types
#Intervention types
int_type = c("area_protect", "area_mgmt", "res_mgmt", "sp_control", "restoration", "sp_mgmt", "sp_recov", "sp_reint", "ex_situ", "form_ed", "training", "aware_comm", "legis", "pol_reg", "priv_codes", "compl_enfor", "liv_alt", "sub", "market", "non_mon", "inst_civ_dev", "part_dev", "cons_fin", "sus_use", "other")

#Create blank data matrix with labeled rows and columns
int_counts <- matrix(nrow=25, ncol=1)
rownames(int_counts) <- int_type
colnames(int_counts) <- c("counts")
#Calculate in for loop and write to blank matrix
for (i in int_type){
  subset <- filter(data.interv, Int_type == i)
  int_counts[i,1] <- n_distinct(subset$aid)
}
#Remove rownames and reformat data types
int_counts <- as.data.frame(int_counts)
icounts <- as.numeric(int_counts$counts)
int_labels = c("Area protection", "Area management", "Resource management/protection", "Species control", "Restoration", "Species management", "Species recovery", "Species reintroduction", "Ex-situ conservation", "Formal education", "Training", "Awareness & Communications", "Legislation", "Policies & Regulations", "Private sector standards and codes", "Compliance & enforcement", "Enterprises & livelihood alternatives", "Substitution", "Market-based forces", "Non-monetary values", "Institutional & civil society development", "Alliance & partnership development", "Conservation finance", "Sustainable use", "Other")

#Create barplot
pdf(file="Summary_interventions.pdf")
par(mar = c(7, 4, 2, 2) + 0.2)
end_point = 0.5 + nrow(int_counts) + nrow(int_counts)-1
barplot(icounts, main="Intervention types", axes=TRUE, ylim = c(0,5+max(icounts)), ylab = "Number of studies", xlab = "", col="turquoise", angle=45, border=NA, space=1)
text(seq(1.5,end_point,by=2), par("usr")[3]-0.25, srt=60, adj=1, xpd=TRUE, labels = paste(int_labels), cex=0.65)
box()
dev.off()

#Outcome types
out_type = c("env", "mat_liv_std", "eco_liv_std", "health", "education", "soc_rel", "sec_saf", "gov", "sub_well", "culture", "free_choice", "other")
#Create blank data matrix with labeled rows and columns
out_counts <- matrix(nrow=12, ncol=1)
rownames(out_counts) <- out_type
colnames(out_counts) <- c("counts")
#Calculate in for loop and write to blank matrix
for (o in out_type){
  subset <- filter(data.outcome, Outcome == o)
  out_counts[o,1] <- n_distinct(subset$aid)
}
#Remove rownames and reformat data types
out_counts <- as.data.frame(out_counts)
ocounts <- as.numeric(out_counts$counts)
out_labels = c("Environmental", "Material living standards", "Economic living standards", "Health", "Education", "Social relations", "Security & safety", "Governance & empowerment", "Subjective well-being", "Culture & Spiritual", "Freedom of choice/action", "Other")

#Create barplot
pdf(file="Summary_outcomes.pdf")
par(mar = c(7, 4, 2, 2) + 0.2)
end_point = 0.5 + nrow(out_counts) + nrow(out_counts)-1
barplot(ocounts, main="Outcome types", axes=TRUE, ylim = c(0,5+max(ocounts)), ylab = "Number of studies", xlab = "", col="turquoise", angle=45, border=NA, space=1)
text(seq(1.5,end_point,by=2), par("usr")[3]-0.25, srt=60, adj=1, xpd=TRUE, labels = paste(out_labels), cex=0.65)
box()
dev.off()

##Heatmap of incidences between intervention + HWB
#Load required packages
library(gplots)
library(RColorBrewer)
#Create new dataframe with intervention and outcome data
int_out <- left_join(data.interv, data.outcome, by = "aid")
int_out <- select(int_out,aid,Int_type,Outcome)
#Create blank data matrix with labeled rows and columns
int_type = c("area_protect", "area_mgmt", "res_mgmt", "sp_control", "restoration", "sp_mgmt", "sp_recov", "sp_reint", "ex_situ", "form_ed", "training", "aware_comm", "legis", "pol_reg", "priv_codes", "compl_enfor", "liv_alt", "sub", "market", "non_mon", "inst_civ_dev", "part_dev", "cons_fin", "sus_use", "other")
out_type = c("env", "mat_liv_std", "eco_liv_std", "health", "education", "soc_rel", "sec_saf", "gov", "sub_well", "culture", "free_choice", "other")
io_counts = matrix(nrow=12, ncol=25)
rownames(io_counts) <- out_type
colnames(io_counts) <- int_type
#Calculate number of unique studies for each linkage cell between intervention and outcome
#Calculate in for loop and write to blank matrix
for (i in int_type){
  for (j in out_type){
    subset <- filter(int_out, Outcome == j, Int_type == i)
    io_counts[j,i] <- n_distinct(subset$aid)
  }
}
#Relabel rows and columns
int_labels = c("Area protection", "Area management", "Resource management/protection", "Species control", "Restoration", "Species management", "Species recovery", "Species reintroduction", "Ex-situ conservation", "Formal education", "Training", "Awareness & Communications", "Legislation", "Policies & Regulations", "Private sector standards and codes", "Compliance & enforcement", "Enterprises & livelihood alternatives", "Substitution", "Market-based forces", "Non-monetary values", "Institutional & civil society development", "Alliance & partnership development", "Conservation finance", "Sustainable use", "Other")
out_labels = c("Environmental", "Material living standards", "Economic living standards", "Health", "Education", "Social relations", "Security & safety", "Governance & empowerment", "Subjective well-being", "Culture & Spiritual", "Freedom of choice/action", "Other")
rownames(io_counts) <- out_labels
colnames(io_counts) <- int_labels
#Define color palette for heatmap
palette <- colorRampPalette(c("red", "yellow", "green")) (n=299)
palette1 <- colorRampPalette(c("#ffffcc", "#c7e9b4", "#7fcdbb", "#41b6c4", "#1d91c0", "#225ea8", "#0c2c84")) (n=299)
palette2 <- colorRampPalette(c("#762a83", "#af8dc3", "#c7eae5", "#5ab4ac", "#01665e")) (n=299)
palette3 <- colorRampPalette(c("#b2182b", "#ef8a62", "#fddbc7", "#f7f7f7", "#d1e5f0", "#67a9cf", "#2166ac")) (n=299)
palette4 <- colorRampPalette(c("#cef3f7", "#9ce7ee", "#39cedd", "#3796a0", "#04616a", "#023035")) (n=299)
palette5 <- colorRampPalette(c("#e66101", "#fdb863", "#f7f7f7","#f7f7f7", "#b2abd2", "#5e3c99")) (n=50)
palette6 <- colorRampPalette(c("#636363", "#CCCCCC", "#f7f7f7","#f7f7f7", "#80cdc1", "#018571")) (n=50)

#Write heatmap and legend to PDF
pdf(file="Interventions_Outcomes_Heatmap_3.pdf", width=11, height=8.5)
heatmap.2(io_counts, Colv=NA, dendrogram="none", col=palette6, cellnote=io_counts, notecol="gray", notecex=0.5, trace="none", cexRow=1.5, cexCol=1.5, key=TRUE, Rowv=NA)
dev.off()

##Heatmap of incidences between intervention + biomes
#Load required packages
library(gplots)
library(RColorBrewer)
#Create new dataframe with intervention and biome data
int_biome <- left_join(data.interv, data.biomes, by = "aid")
int_biome <- select(int_biome,aid,Int_type,Biome.)
#Create blank data matrix with labeled rows and columns
int_type = c("area_protect", "area_mgmt", "res_mgmt", "sp_control", "restoration", "sp_mgmt", "sp_recov", "sp_reint", "ex_situ", "form_ed", "training", "aware_comm", "legis", "pol_reg", "priv_codes", "compl_enfor", "liv_alt", "sub", "market", "non_mon", "inst_civ_dev", "part_dev", "cons_fin", "sus_use", "other")
biome_type = c("T_TSTMBF", "T_TSTDBF", "T_TSTCF", "T_TBMF", "T_TCF", "T_BFT", "T_TSTGSS", "T_TGSS", "T_FGS", "T_MGS", "T_T", "T_MFWS", "T_DXS", "T_M", "FW_LL", "FW_SL", "FW_LR", "FW_LRH", "FW_LRD", "FW_SR", "FW_XB", "M_P", "M_TSS", "M_TU", "M_TRU", "M_TRC", "M_TSTSS")
ib_counts = matrix(nrow=27, ncol=25)
rownames(ib_counts) <- biome_type
colnames(ib_counts) <- int_type
#Calculate number of unique studies for each linkage cell between intervention and outcome
#Calculate in for loop and write to blank matrix
for (i in int_type){
  for (j in biome_type){
    subset <- filter(int_biome, Biome. == j, Int_type == i)
    ib_counts[j,i] <- n_distinct(subset$aid)
  }
}
#Relabel rows and columns
int_labels = c("Area protection", "Area management", "Resource management/protection", "Species control", "Restoration", "Species management", "Species recovery", "Species reintroduction", "Ex-situ conservation", "Formal education", "Training", "Awareness & Communications", "Legislation", "Policies & Regulations", "Private sector standards and codes", "Compliance & enforcement", "Enterprises & livelihood alternatives", "Substitution", "Market-based forces", "Non-monetary values", "Institutional & civil society development", "Alliance & partnership development", "Conservation finance", "Sustainable use", "Other")
biome_labels = c("Tropical/sub-tropical moist broadleaf forests", "Tropical/sub-tropical dry broadleaf forests", "Tropical/sub-tropical coniferous forests", "Temperate broadleaf and mixed forests", "Temperate coniferous forests", "Boreal forests & taiga", "Tropical/sub-tropical grasslands, savannas & shrublands", "Temperate grasslands, savannas & shrublands", "Flooded grasslands and savannas", "Montane grasslands & shrublands", "Tundra", "Mediterranean forests, woodlands & scrubs", "Deserts & xeric shrublands", "Mangroves", "Large lakes", "Small lakes", "Large rivers", "Large river headwaters", "Large river deltas", "Small rivers", "Xeric basins", "Marine-polar", "Marine-temperate shelfs and seas", "Marine-temperate upwelling", "Marine-tropical upwelling", "Marine-tropical corals", "Marine-tropical shelfs and seas")
rownames(ib_counts) <- biome_labels
colnames(ib_counts) <- int_labels
#Define color palette for heatmap
palette <- colorRampPalette(c("white", "paleturquoise1", "paleturquoise3", "turquoise2", "turquoise4", "darkslategray4", "darkslategray")) (n=299)
#Write heatmap and legend to PDF
pdf(file="Interventions_Biomes_Heatmap.pdf", width=11, height=8.5)
heatmap.2(ib_counts, Colv=NA, dendrogram="none", col=palette, cellnote=ib_counts, notecol="black", notecex=1.0, trace="none", cexRow=1.5, cexCol=1.5, key=TRUE, Rowv=NA)
dev.off()

##Heatmap of incidences between intervention + HWB w/ conceptual model
#Load required packages
library(gplots)
library(RColorBrewer)
#Create new dataframe with intervention and outcome data
concept <- select(data.pathways,aid,Concept_mod)
int_out_c <- left_join(data.interv, data.outcome,by = "aid")
int_out_c <- left_join(int_out_c,concept,by="aid")
int_out_c <- select(int_out_c,aid,Int_type,Outcome,Concept_mod)
#Create blank data matrix with labeled rows and columns
int_type = c("area_protect", "area_mgmt", "res_mgmt", "sp_control", "restoration", "sp_mgmt", "sp_recov", "sp_reint", "ex_situ", "form_ed", "training", "aware_comm", "legis", "pol_reg", "priv_codes", "compl_enfor", "liv_alt", "sub", "market", "non_mon", "inst_civ_dev", "part_dev", "cons_fin", "sus_use", "other")
out_type = c("env", "mat_liv_std", "eco_liv_std", "health", "education", "soc_rel", "sec_saf", "gov", "sub_well", "culture", "free_choice", "other")
ioc_counts = matrix(nrow=12, ncol=25)
rownames(ioc_counts) <- out_type
colnames(ioc_counts) <- int_type
#Calculate number of unique studies for each linkage cell between intervention and outcome
#Calculate in for loop and write to blank matrix
for (i in int_type){
  for (j in out_type){
    subset <- filter(int_out, Outcome == j, Int_type == i)
    subset_c <- filter(int_out, Outcome == j, Int_type == i, Concept_mod == 1)
    percent <- (n_distinct(subset_c$aid) / n_distinct(subset$aid))*100
    ioc_counts[j,i] <- percent
  }
}
#Relabel rows and columns
int_labels = c("Area protection", "Area management", "Resource management/protection", "Species control", "Restoration", "Species management", "Species recovery", "Species reintroduction", "Ex-situ conservation", "Formal education", "Training", "Awareness & Communications", "Legislation", "Policies & Regulations", "Private sector standards and codes", "Compliance & enforcement", "Enterprises & livelihood alternatives", "Substitution", "Market-based forces", "Non-monetary values", "Institutional & civil society development", "Alliance & partnership development", "Conservation finance", "Sustainable use", "Other")
out_labels = c("Environmental", "Material living standards", "Economic living standards", "Health", "Education", "Social relations", "Security & safety", "Governance & empowerment", "Subjective well-being", "Culture & Spiritual", "Freedom of choice/action", "Other")
rownames(ioc_counts) <- out_labels
colnames(ioc_counts) <- int_labels
#Define color palette for heatmap
palette <- colorRampPalette(c("white", "paleturquoise1", "paleturquoise3", "turquoise2", "turquoise4", "darkslategray4", "darkslategray")) (n=299)
#Write heatmap and legend to PDF
pdf(file="Interventions_Outcomes_wConcept_Heatmap.pdf", width=11, height=8.5)
heatmap.2(ioc_counts, Colv=NA, dendrogram="none", col=palette, cellnote=ioc_counts, notecol="black", notecex=1.0, trace="none", cexRow=1.5, cexCol=1.5, key=TRUE, Rowv=NA)
dev.off()

##Conceptual models
concept <- distinct(select(data.pathways,aid,Concept_mod))
mod <- count(concept,Concept_mod)
model <- as.numeric(as.vector(mod[2,2]))
none <- as.numeric(as.vector(mod[1,2]))
unk <- as.numeric(as.vector(mod[3,2]))
slices <- c(model,unk,none)
lbls <- c("Conceptual model", "Unknown", "None")
pct <- round(slices/sum(slices)*100)
lbls <- paste(lbls,"(",pct,sep="")
lbls <- paste(lbls,"%)",sep="")
pdf(file="Conceptual_models.pdf",width=11, height=8.5)
pie(slices,labels=lbls,main="Studies employing conceptual models")
dev.off()

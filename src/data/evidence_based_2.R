##Set up environment and constants
library(dplyr)
library(tidyr)
path <- "~/Documents/CI_Projects_LA/Knowledge_Base/"
lut.file <- "questions_LU_cat.csv"
csv.file <- "Data_Final_02_11_2016_Eng_only.csv"
csv <- paste(path, csv.file, sep="")
lut <- paste(path, lut.file, sep="")

##Define functions
#Move column to end or beginning of the dataframe
move.column <- function(data, tomove, where = "last", ba = NULL) {
temp <- setdiff(names(data), tomove)
df.new <- switch(where,
first = data[c(tomove, temp)],
last = data[c(temp, tomove)])
return(df.new)
}
#Subset the data based on categories of the Look-up table (LUT)
cat.subsetter <- function(dataset,expr){
fields <- lut.cat %>% filter_(expr) %>% select(Field_name)
list <- list(fields[[1]])[[1]]
data.new <- dataset[,colnames(dataset) %in% list]
return(data.new)
}
#Summarise the data per column (does not group by article)
summarizer <- function(dataset, fun.name){
col.to.merge <- colnames(dataset)
#Create a list of it
dots <- lapply(col.to.merge, as.symbol)
data.out <- dataset %>% summarise_each(funs(fun.name))
data.out <- gather_(data.out,"field", as.character(substitute(fun.name)), dots)
return(data.out)
}
#Summarise the data per journal article and creates a character list of all the values of the article
summarizer.list <- function(dataset){
#new.field <- paste(field, "n", sep="_")
data.l <- dataset %>% group_by(aid) %>% summarise_each(funs(toString))
data.n <-  dataset %>% group_by(aid) %>% summarise_each(funs(n_distinct))
data.out <- full_join(data.l, data.n, by="aid")
return(data.out)
}
#List the unique values accross the whole table (ie, all the journal articles)
summarizer.list.all <- function(dataset, fields){
summarise_each(dataset, funs(ul=toString(sort(unique(.))))) %>%
gather_("field", "valuesList",fields) %>%
select(field, valuesList)
}
##Summarise information groupiing by journal article with option to use two functions in a row, then gather the information to transpose the dataframe with fields used as rows
summarizer.groupby <- function(dataset, fun.name, fun.name2=NULL){
#List the column names
col.to.merge <- colnames(dataset)
#Create a list of symbols from the column names
dots <- lapply(col.to.merge[2:length(col.to.merge)], as.symbol)
if (is.null(fun.name2)){
data.out <- dataset  %>% summarise_each(funs(fun.name))
data.out <- gather_(data.out,"field", as.character(substitute(fun.name)), dots) %>% select(-aid)
} else {
data.out <- dataset  %>% group_by(aid) %>% summarise_each(funs(fun.name)) %>% summarise_each(funs(fun.name2))
data.out <- gather_(data.out,"field", as.character(substitute(fun.name2)), dots) %>% select(-aid)
}
return(data.out)
}
##Merge the multi-value binary coded fields into one column with repeated entries
combine.binfield <- function(datasubset,field, delete.option=1){
#Get the binary fields
#data.bin <- datasubset %>% select(contains(field))
data.bin <- datasubset %>% select(starts_with(field))
col.to.merge <- colnames(data.bin)
#Create a list of it
dots <- lapply(col.to.merge, as.symbol)
#Keep only the binary columns
data.bin <-  datasubset[,colnames(datasubset) %in% c("aid",col.to.merge)]
#Merge the binary fields
#data.binlong <- datasubset %>% gather_(field, "have", dots)
data.binlong <- data.bin %>% gather_(field, "have", dots)
#test to delete the rows with 0
if (delete.option == 1) {
data.binlong <- data.binlong %>% filter(have==1) %>% separate_(field, c("prefix",field), sep = "\\.")
} else {
data.binlong <- data.binlong %>% separate_(field, c("prefix",field), sep = "\\.")
data.binlong[,field] <- ifelse(data.binlong$have == 0,NA, data.binlong[,field])
data.binlong <- unique(data.binlong)
}
#Remove the temporary fields
data.binlong$prefix <- NULL
data.binlong$have <- NULL
#transform aid to numeric
data.binlong <- data.binlong %>% transform(aid = as.integer(aid))
#Sort data using aid
data.binlong <- arrange(data.binlong,aid)
return(data.binlong)
}

##Read in data and subset
data <- read.csv(csv, head=TRUE, sep=",", colClasses="character")
# Look-up table with the categories and attributes
lut.cat <- read.csv(lut, head=TRUE, sep=",", colClasses="character")
#list field names
field.names <- colnames(data)
data.biblio.raw <- cat.subsetter(data,quote(Category == "index" | Category == "A" | Category == "R"))
data.interv.raw <- cat.subsetter(data,quote(Category == "index" | Category == "I"))
data.study.raw <- cat.subsetter(data,quote(Category == "index" | Category == "S"))
data.outcome.raw <- cat.subsetter(data,quote(Category == "index" | Category == "O"))
data.outhwb.raw <- cat.subsetter(data,quote(Category == "index" | Category == "WB"))
data.pathways.raw <- cat.subsetter(data,quote(Category == "index" | Category == "P"))
data.biomes.study <- cat.subsetter(data,quote(Category == "index" | Category == "BS"))
##Merge multivalued fields
##Bibliographic information
data.biblio.affil <- combine.binfield(data.biblio.raw, "Affil_type")
#Summarise the data
summary.byaid <- summarizer.list(data.biblio.affil)
#Remove the binary fields from the raw data
data.biblio <- select(data.biblio.raw,-starts_with("Affil_type"))  %>%
  transform(aid = as.integer(aid))
#Join the table
data.biblio <- full_join(data.biblio, data.biblio.affil, by="aid")
#Move the note column to the end
data.biblio <- move.column(data.biblio, "Bib_notes")
#cleanup
rm(list=ls(pattern="data.biblio."))

##Intervention
#intervention type
#Combine the binary fields
data.interv.Int <- combine.binfield(data.interv.raw, "Int_type")
#Summarise the data
summary.byaid <- summarizer.list(data.interv.Int) %>% right_join(summary.byaid,by="aid")

#implementation type
#Combine the binary fields
data.interv.Impl <- combine.binfield(data.interv.raw, "Impl_type")
#Summarise the data
summary.byaid <- summarizer.list(data.interv.Impl) %>% right_join(summary.byaid,by="aid")

#Merge the binary cases
data.interv.combined <- full_join(data.interv.Int, data.interv.Impl, by="aid")
#Remove the binary fields from the raw data
data.interv <- select(data.interv.raw,-starts_with("Int_type")) %>%
  select(-starts_with("Impl_type")) %>% 
  transform(aid = as.integer(aid))
#Join the table
data.interv <- full_join(data.interv, data.interv.combined, by="aid")
#Move the note column to the end
data.interv <- move.column(data.interv, "Desired_outcome")
data.interv <- move.column(data.interv, "Int_notes")
#cleanup
rm(list=ls(pattern="data.interv."))

##Study information
#Data source
#Combine the binary fields
data.study.source <- combine.binfield(data.study.raw, "Data_source")
#Summarise the data
summary.byaid <- summarizer.list(data.study.source) %>% right_join(summary.byaid,by="aid")

#Evalaluation affiliation type
#Combine the binary fields
data.study.affil <- combine.binfield(data.study.raw, "Eval_affil_type")
#Summarise the data
summary.byaid <- summarizer.list(data.study.affil) %>% right_join(summary.byaid,by="aid")

#Evalaluation affiliation type
#Combine the binary fields
data.study.type <- combine.binfield(data.study.raw, "Data_type")
#Summarise the data
summary.byaid <- summarizer.list(data.study.type) %>% right_join(summary.byaid,by="aid")

#Marginal groups
#Combine the binary fields
data.study.marg <- combine.binfield(data.study.raw, "Marg_groups.") %>% rename(Marg_cat = Marg_groups.)
#Summarise the data
summary.byaid <- summarizer.list(data.study.marg) %>% right_join(summary.byaid,by="aid")
#Merge the binary cases
data.study.combined <- full_join(data.study.affil, data.study.marg, by="aid") %>% full_join(data.study.source, by="aid") %>% full_join(data.study.type, by="aid")
#Remove the binary fields from the raw data
data.study <- select(data.study.raw,-starts_with("Eval_affil_type")) %>%
  select(-starts_with("Marg_groups.")) %>% select(-starts_with("Data_source")) %>% select(-starts_with("Data_type")) %>% transform(aid = as.integer(aid))
#Join the table
data.study <- full_join(data.study, data.study.combined, by="aid")
#Move the note column to the end
data.study <- move.column(data.study, "Study_location") 
data.study <- move.column(data.study, "Study_notes") 
#cleanup
rm(list=ls(pattern="data.study."))

##Outcomes
#Outcome type
#Combine the binary fields
data.outcome <- combine.binfield(data.outcome.raw, "Outcome.")
#Summarise the data
summary.byaid <- summarizer.list(data.outcome) %>% right_join(summary.byaid,by="aid")
#
#Move the note column to the end
#Join the table
data.outcome <- select(data.outcome.raw,aid,Equity,Equity_cat,Outcome_notes) %>% 
  transform(aid = as.integer(aid)) %>% arrange(aid) %>% 
  full_join(data.outcome,by="aid")
data.outcome <- move.column(data.outcome, "Outcome_notes") %>% rename(Outcome = Outcome.)
#cleanup
rm(list=ls(pattern="data.outcome."))

##Individual outcomes and impacts
#subset and rename the fields
outcome1 <- data.outhwb.raw %>% select(aid,starts_with("Outcome1"))
colnames(outcome1) <- c("aid", "OutcomeHWB.gen_cat", "OutcomeHWB.spec_cat", "OutcomeHWB.groups", "OutcomeHWB.Data_type", "OutcomeHWB.Percept", "OutcomeHWB.Equity", "OutcomeHWB", "OutcomeHWB.impact")
outcome2 <- data.outhwb.raw %>% select(aid,starts_with("Outcome2"))
colnames(outcome2) <- c("aid", "OutcomeHWB.gen_cat", "OutcomeHWB.spec_cat", "OutcomeHWB.groups", "OutcomeHWB.Data_type", "OutcomeHWB.Percept", "OutcomeHWB.Equity", "OutcomeHWB", "OutcomeHWB.impact")
outcome3 <- data.outhwb.raw %>% select(aid,starts_with("Outcome3"))
colnames(outcome3) <- c("aid", "OutcomeHWB.gen_cat", "OutcomeHWB.spec_cat", "OutcomeHWB.groups", "OutcomeHWB.Data_type", "OutcomeHWB.Percept", "OutcomeHWB.Equity", "OutcomeHWB", "OutcomeHWB.impact")
outcome4 <- data.outhwb.raw %>% select(aid,starts_with("Outcome4"))
colnames(outcome4) <- c("aid", "OutcomeHWB.gen_cat", "OutcomeHWB.spec_cat", "OutcomeHWB.groups", "OutcomeHWB.Data_type", "OutcomeHWB.Percept", "OutcomeHWB.Equity", "OutcomeHWB", "OutcomeHWB.impact")
outcome5 <- data.outhwb.raw %>% select(aid,starts_with("Outcome5"))
colnames(outcome5) <- c("aid", "OutcomeHWB.gen_cat", "OutcomeHWB.spec_cat", "OutcomeHWB.groups", "OutcomeHWB.Data_type", "OutcomeHWB.Percept", "OutcomeHWB.Equity", "OutcomeHWB", "OutcomeHWB.impact")
#union the outcomes
data.outhwb <-  bind_rows(outcome1,outcome2) %>% bind_rows(outcome3) %>% bind_rows(outcome4) %>% bind_rows(outcome5)
data.outhwb <- filter(data.outhwb,OutcomeHWB != "")
#Transform aid into numeric and sort
data.outhwb <- data.outhwb %>% transform(aid = as.integer(aid)) %>% arrange(aid)
#Keep perception binary
data.outhwb$OutcomeHWB.Percept[is.na(data.outhwb$OutcomeHWB.Percept)] <- 0
data.outhwb$OutcomeHWB.Equity[is.na(data.outhwb$OutcomeHWB.Equity)] <- 0
#summarise data
summary.byaid <- summarizer.list(data.outhwb) %>% right_join(summary.byaid,by="aid")
#clean up
rm(outcome1, outcome2, outcome3, outcome4, outcome5)

##Biomes
#Combine the binary fields
data.biomes <- combine.binfield(data.biomes.study, "Biome.")
#Summarise the data
summary.byaid <- summarizer.list(data.biomes) %>% right_join(summary.byaid,by="aid")
#cleanup
rm(list=ls(pattern="data.biomes.study"))

##Pathways
# Ecosystem service type
#Combine the binary fields
data.pathways.es <- combine.binfield(data.pathways.raw, "ES.") %>% rename(ES_type = ES.)
summary.byaid <- summarizer.list(data.pathways.es) %>% right_join(summary.byaid,by="aid")
#Subtype
#Combine the binary fields
data.pathways.type <- combine.binfield(data.pathways.raw, "ES_type") %>% rename(ES_subtype = ES_type)
summary.byaid <- summarizer.list(data.pathways.type) %>% right_join(summary.byaid,by="aid")
#Disservices
#Combine the binary fields
data.pathways.diss <- combine.binfield(data.pathways.raw, "Disservices.") %>% rename(Disservices = Disservices.)
summary.byaid <- summarizer.list(data.pathways.diss) %>% right_join(summary.byaid,by="aid")
#Merge the binary cases
#Left_join is used because if there is no ES, the other fields are null too
data.pathways.combined <- left_join(data.pathways.es,data.pathways.type, by="aid") %>%
  left_join(data.pathways.diss, by="aid")
#Remove the binary fields from the raw data
data.pathways <- select(data.pathways.raw,-starts_with("ES.")) %>%
  select(-starts_with("ES_type")) %>% select(-starts_with("Disservices.")) %>%
  transform(aid = as.integer(aid))
#Join the table
data.pathways <- full_join(data.pathways, data.pathways.combined, by="aid")
#Move the note column to the end
data.pathways <- move.column(data.pathways, "Pathway_notes")
#set empty fields to NA
data.pathways$Factor_type[data.pathways$Factor_type ==""] <- NA
#cleanup
rm(list=ls(pattern="data.pathways."))

##Summarise data
##Bibliographic
#Compute the the maximal number of values per multivalued field
#summary.all <- summarizer.groupby(data.biblio, n_distinct, max)
data.occurencel <- summarizer.list.all(data.biblio, c("Assessor","Assessor_2","Pub_type", "Affil_type"))
##Intervention
#Compute the the maximal number of values per multivalued field
summary.all <- summarizer.groupby(data.interv, n_distinct, max)
#list all the values accross the reviewd papers per multivalued field
data.occurencel <- summarizer.list.all(data.interv, c("Int_area", "Int_geo", "Int_dur", "Int_type", "Impl_type"))
##Study
#Compute the the maximal number of values per multivalued field
summary.all <- summarizer.groupby(data.study, n_distinct, max) %>% bind_rows(summary.all)
#list all the values accross the reviewd papers per multivalued field
data.occurencel <- summarizer.list.all(data.study, c("Data_source", "Eval_affil_type", "Marg_cat", "Comps")) %>%
  bind_rows(data.occurencel)
##Biome
#Compute the the maximal number of values per multivalued field
summary.all <- summarizer.groupby(data.biomes, n_distinct, max) %>% bind_rows(summary.all)
#list all the values accross the reviewd papers per multivalued field
data.occurencel <- summarizer.list.all(data.biomes, c("Biome.")) %>% bind_rows(data.occurencel)
##Outcome
#Compute the the maximal number of values per multivalued field
summary.all <- summarizer.groupby(data.outcome, n_distinct, max) %>% bind_rows(summary.all)
#list all the values accross the reviewd papers per multivalued field
data.occurencel <- summarizer.list.all(data.outcome,"Outcome") %>%
  bind_rows(data.occurencel)
##Specific outcomes and impacts
#Compute the the maximal number of values per multivalued field
summary.all <- summarizer.groupby(data.outhwb, n_distinct, max) %>% bind_rows(summary.all)
#list all the values accross the reviewd papers per multivalued field
data.occurencel <- summarizer.list.all(data.outhwb,c("OutcomeHWB.gen_cat", "OutcomeHWB.spec_cat", "OutcomeHWB.groups", "OutcomeHWB.Data_type", "OutcomeHWB.Percept", "OutcomeHWB.Equity", "OutcomeHWB", "OutcomeHWB.impact")) %>% bind_rows(data.occurencel)
##Pathways
#Compute the the maximal number of values per multivalued field
summary.all <- summarizer.groupby(data.pathways, n_distinct, max) %>% bind_rows(summary.all)
#list all the values accross the reviewd papers per multivalued field
data.occurencel <- summarizer.list.all(data.pathways, c("Concept_mod_name", "Factors","Factor_type", "ES_mechanism","ES_type","ES_subtype", "Disservices")) %>%
  bind_rows(data.occurencel)
##Clean up summaries
#Remove aid duplicates
summary.all <- distinct(summary.all)
#join the max and values list
summary.all <- left_join(summary.all,data.occurencel,by="field")
##Rename summary fields by journal articles

##Write final R data and package
save(data.biblio,data.interv,data.study,data.biomes,data.outcome,data.outhwb,data.pathways,
     summary.byaid, summary.all, file = paste(path, "evidence_based_2_11_16.RData", sep=""))
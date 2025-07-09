# Databricks notebook source
print('hello world')

# COMMAND ----------

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, sum, avg, when, countDistinct, desc, rank,datediff, weekofyear, month, year, dayofweek, lit,  concat
from pyspark.sql.window import Window

# COMMAND ----------

# Initialize Spark session
spark = SparkSession.builder.appName("GoldLayerTransformations").getOrCreate()

# COMMAND ----------


df_books = spark.read.table("`lms-catalog`.silver.books")
df_books_copies = spark.read.table("`lms-catalog`.silver.books_copies")
df_students = spark.read.table("`lms-catalog`.silver.students")
df_transactions = spark.read.table("`lms-catalog`.silver.transactions")
display(df_books)
display(df_books_copies)
display(df_students)
display(df_transactions)

# COMMAND ----------

# Join tables on book_id
df_joined = df_books.join(df_books_copies, "book_id", "inner").display()

# COMMAND ----------

# Total Books & Copies
total_books = df_books.select(countDistinct("book_id").alias("total_books")).collect()[0]["total_books"]
total_copies = df_books_copies.select(count("copy_id").alias("total_copies")).collect()[0]["total_copies"]
display(total_books, total_copies)

# COMMAND ----------

# Books by Department
df_books_by_department = df_books.groupBy("department").count().withColumnRenamed("count", "book_count")
display(df_books_by_department)

# COMMAND ----------

# Books by Availability
df_books_by_status = df_books_copies.groupBy("status").count().withColumnRenamed("count", "status_count")
display(df_books_by_status)

# COMMAND ----------

# Top Authors & Publishers
df_top_authors = df_books.groupBy("author").count().orderBy(desc("count")).limit(10)
df_top_publishers = df_books.groupBy("publisher").count().orderBy(desc("count")).limit(10)
display(df_top_authors, df_top_publishers)

# COMMAND ----------

# Most Popular Books (Based on Copies)
window_spec = Window.orderBy(desc("copy_count"))
df_book_popularity = df_books_copies.groupBy("book_id").count().withColumnRenamed("count", "copy_count")
df_book_popularity = df_book_popularity.withColumn("rank", rank().over(window_spec)).limit(10)
df_book_popularity = df_book_popularity.join(df_books.select("book_id", "book_title"), "book_id")
df_book_popularity.show()


# COMMAND ----------

# Book Distribution by Location
df_location_distribution = df_books_copies.groupBy("location", "rack", "shelf").count().withColumnRenamed("count", "books_count")
df_location_distribution.show()

# COMMAND ----------

# Results Summary
print(f"Total Books: {total_books}, Total Copies: {total_copies}")

# COMMAND ----------


# Step 1: Join books_table and book_copies_table (Using INNER JOIN) -> books_final_table
books_final_table = df_books.join(df_books_copies, on="book_id", how="inner")


# COMMAND ----------

# Step 2: Join books_final_table and transaction_table (Using LEFT JOIN) -> books_transaction_table
books_transaction_table = books_final_table.join(df_transactions, on=["book_id", "copy_id"], how="left")
# books_transaction_table = books_final_table.join(df_transactions_q3, on=["book_id", "copy_id"], how="left")
# books_transaction_table = books_final_table.join(df_transactions_q4, on=["book_id", "copy_id"], how="left")
display(books_transaction_table)


# COMMAND ----------

# Step 3: Join students_table and transaction_table (Using RIGHT JOIN) -> student_transaction_table
student_transaction_table = df_students.join(df_transactions, on="student_id", how="right")
display(student_transaction_table)

# COMMAND ----------

student_transaction_table.columns

# COMMAND ----------

books_transaction_table.columns

# COMMAND ----------

# Step 4: Transformations on books_transaction_table
# Example: Count total transactions per book
book_transaction_counts = books_transaction_table.groupBy("book_title").agg(count("transaction_id").alias("total_transactions"))
display(book_transaction_counts)


# COMMAND ----------

# Example: Calculate average fine per book
avg_fine_per_book = books_transaction_table.groupBy("book_title").agg(avg("fine_amount").alias("average_fine"))
display(avg_fine_per_book)

# COMMAND ----------

# Example: Average fine per student
avg_fine_per_student = student_transaction_table.groupBy("student_id").agg(avg("fine_amount").alias("average_fine"))
display(avg_fine_per_student)

# COMMAND ----------

# MAGIC %md
# MAGIC #Insights

# COMMAND ----------

# Read datasets from Azure Data Lake Storage
books_df = spark.read.format("delta").load("abfss://silver@lmsstorageaccount2025.dfs.core.windows.net/books")
book_copies_df = spark.read.format("delta").load("abfss://silver@lmsstorageaccount2025.dfs.core.windows.net/books_copies")
students_df = spark.read.format("delta").load("abfss://silver@lmsstorageaccount2025.dfs.core.windows.net/students")
transactions_df = spark.read.table("`lms-catalog`.silver.transactions")


# COMMAND ----------

# Merging books_table, book_copies_table, and transactions_table for book insights using various joins
books_transaction_table = books_df.join(book_copies_df, "book_id", "inner")\
                                   .join(transactions_df, ["book_id", "copy_id"], "right")
display(books_transaction_table)

# COMMAND ----------

books_transaction_table.write.format("delta").mode("overwrite").save("abfss://gold@lmsstorageaccount2025.dfs.core.windows.net/books_transaction_table")

# COMMAND ----------

# MAGIC %sql
# MAGIC DROP TABLE IF EXISTS `lms-catalog`.gold.books_transaction_table;
# MAGIC
# MAGIC CREATE TABLE `lms-catalog`.gold.books_transaction_table
# MAGIC USING DELTA
# MAGIC LOCATION 'abfss://gold@lmsstorageaccount2025.dfs.core.windows.net/books_transaction_table';

# COMMAND ----------

# Merging students_table and transactions_table for student insights using different joins
students_transaction_table = students_df.join(transactions_df, "student_id", "outer")


# COMMAND ----------

students_transaction_table.display()

# COMMAND ----------

#Concatinating first_name and last_name as full_name

students_transaction_table = students_transaction_table.withColumn("full_name", concat(col("first_name"), lit(" "), col("last_name")))

# COMMAND ----------

students_transaction_table.write.format("delta").mode("overwrite").save("abfss://gold@lmsstorageaccount2025.dfs.core.windows.net/students_transaction_table")

# COMMAND ----------

# MAGIC %sql
# MAGIC DROP TABLE IF EXISTS `lms-catalog`.gold.students_transaction_table;
# MAGIC
# MAGIC CREATE TABLE `lms-catalog`.gold.students_transaction_table
# MAGIC USING DELTA
# MAGIC LOCATION 'abfss://gold@lmsstorageaccount2025.dfs.core.windows.net/students_transaction_table';

# COMMAND ----------

# Load the books_transaction_table
# books_transaction_table = spark.table("books_transaction_table")

# Generating insights for books
# from pyspark.sql.functions import count, col

books_transaction_table.groupBy("book_id").agg(
    count("transaction_id").alias("Total Borrows")
).orderBy(col("Total Borrows").desc()).show()

# COMMAND ----------

books_transaction_table.groupBy("department").agg(count("book_id").alias("Books Borrowed")).show()


# COMMAND ----------

books_transaction_table.withColumn("borrowing_duration", datediff(col("return_date"), col("issue_date")))\
    .groupBy("book_id").agg(avg("borrowing_duration").alias("avg_duration")).show()


# COMMAND ----------

transactions_df.withColumn("is_damaged", when(col("final_status") == "damaged", 1).otherwise(0))\
    .groupBy("is_damaged").count().show()


# COMMAND ----------

transactions_df.filter(col("final_status") == "damaged")\
    .groupBy("book_id").count().orderBy(col("count").desc()).show()


# COMMAND ----------


books_transaction_table.groupBy(month("issue_date").alias("month")).count().orderBy("month").show()



# COMMAND ----------

books_transaction_table.groupBy(weekofyear("issue_date").alias("week")).count().orderBy("week").show()


# COMMAND ----------

books_transaction_table.groupBy(dayofweek("issue_date").alias("day_of_week")).count().orderBy("day_of_week").show()


# COMMAND ----------

display(students_transaction_table)

# COMMAND ----------

# # Ensure students_transaction_table is properly initialized
# students_transaction_table = spark.table("students_transaction_table")
# # Generating insights for students
# from pyspark.sql.functions import col
students_transaction_table.groupBy("student_id").count().orderBy(col("count").desc()).show()

# COMMAND ----------

students_transaction_table.select(sum("fine_amount").alias("Total Fine Collected")).show()


# COMMAND ----------

students_transaction_table.withColumn("is_late", when(col("return_date") > col("due_date"), 1).otherwise(0))\
    .groupBy("is_late").count().show()


# COMMAND ----------

students_transaction_table.groupBy("student_id").agg(sum("fine_amount").alias("total_fine"))\
    .orderBy(col("total_fine").desc()).show()



# COMMAND ----------

students_transaction_table.groupBy("student_id").agg(avg("fine_amount").alias("avg_fine"))\
    .orderBy(col("avg_fine").desc()).limit(10).show()


# COMMAND ----------

students_transaction_table.filter(col("return_date") > col("due_date"))\
    .groupBy("student_id").count().orderBy(col("count")).show()


# COMMAND ----------

students_transaction_table.groupBy("student_id").count()\
    .agg(avg("count").alias("avg_books_per_student")).show()

# COMMAND ----------

student_insights_df = students_transaction_table.groupBy("student_id").agg(
    count("transaction_id").alias("total_borrowed_books"),  # Total books borrowed per student
    sum("fine_amount").alias("total_fine_collected"),  # Total fine collected from each student
    avg("fine_amount").alias("average_fine_per_student"),  # Average fine per student
    count(when(col("return_date") > col("due_date"), 1)).alias("late_returns"),  # Late returns count
    countDistinct("book_id").alias("unique_books_borrowed"),  # Unique books borrowed
    count(when(col("final_status") == "damaged", 1)).alias("damaged_books_returned"),  # Books returned as damaged
    avg(datediff(col("return_date"), col("issue_date"))).alias("avg_borrowing_duration")  # Average borrowing duration
)

# Store the student insights as a Delta table in the catalog
student_insights_df.write.format("delta").mode("overwrite").saveAsTable("`lms-catalog`.gold.student_insights")


# COMMAND ----------

from pyspark.sql.functions import col, count, avg, datediff, when, month, weekofyear, dayofweek

books_insights_table = books_transaction_table.groupBy("book_id").agg(
    count("transaction_id").alias("Total_Borrows"),
    avg(datediff(col("return_date"), col("issue_date"))).alias("avg_duration"),
    count(when(col("final_status") == "damaged", 1)).alias("damaged_copies"),
    count(when(col("return_date") > col("due_date"), 1)).alias("late_returns")
).crossJoin(
    books_transaction_table.groupBy("department").agg(count("book_id").alias("Books_Borrowed")).withColumnRenamed("count", "department_count")
).crossJoin(
    books_transaction_table.groupBy(month("issue_date").alias("month")).count().alias("monthly_borrowing").withColumnRenamed("count", "monthly_count")
).crossJoin(
    books_transaction_table.groupBy(weekofyear("issue_date").alias("week")).count().alias("weekly_borrowing").withColumnRenamed("count", "weekly_count")
).crossJoin(
    books_transaction_table.groupBy(dayofweek("issue_date").alias("day_of_week")).count().alias("daily_borrowing").withColumnRenamed("count", "daily_count")
)

# Store the merged insights table in catalog
books_insights_table.write.mode("overwrite").saveAsTable("`lms-catalog`.gold.books_insights")
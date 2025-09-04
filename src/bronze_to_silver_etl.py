"""
Bronze to Silver ETL Job
Transforms raw data to standardized format with comprehensive data quality validation
Author: Nikitha Shiva
"""

import sys
import json
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Any

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import *
from pyspark.sql.types import *
from awsglue.utils import getResolvedOptions
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.dynamicframe import DynamicFrame

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataQualityValidator:
    """Comprehensive data quality validation framework"""
    
    def __init__(self, spark_session: SparkSession):
        self.spark = spark_session
        self.quality_thresholds = {
            'completeness': 0.90,  # 90% non-null values
            'uniqueness': 0.95,    # 95% unique records
            'validity': 0.90,      # 90% valid data types
            'consistency': 0.85    # 85% consistent formats
        }
    
    def validate_completeness(self, df: DataFrame) -> Dict[str, float]:
        """Check for null values and calculate completeness score"""
        total_records = df.count()
        if total_records == 0:
            return {'completeness_score': 0.0, 'null_counts': {}}
        
        # Calculate null counts for each column
        null_counts = {}
        for col_name in df.columns:
            null_count = df.filter(col(col_name).isNull()).count()
            null_counts[col_name] = null_count
        
        # Overall completeness score
        total_cells = total_records * len(df.columns)
        total_nulls = sum(null_counts.values())
        completeness_score = 1 - (total_nulls / total_cells)
        
        return {
            'completeness_score': completeness_score,
            'null_counts': null_counts,
            'total_records': total_records
        }
    
    def validate_uniqueness(self, df: DataFrame) -> Dict[str, float]:
        """Check for duplicate records"""
        total_records = df.count()
        if total_records == 0:
            return {'uniqueness_score': 1.0}
        
        unique_records = df.dropDuplicates().count()
        uniqueness_score = unique_records / total_records
        
        return {
            'uniqueness_score': uniqueness_score,
            'total_records': total_records,
            'unique_records': unique_records,
            'duplicate_records': total_records - unique_records
        }
    
    def validate_data_types(self, df: DataFrame) -> Dict[str, Any]:
        """Validate data types and formats"""
        validation_results = {}
        
        for col_name, col_type in df.dtypes:
            col_data = df.select(col_name)
            total_count = col_data.count()
            
            if col_type in ['int', 'bigint', 'double', 'float']:
                # Numeric validation
                valid_count = col_data.filter(col(col_name).isNotNull()).count()
            elif col_type == 'string':
                # String validation (non-empty strings)
                valid_count = col_data.filter(
                    (col(col_name).isNotNull()) & (col(col_name) != "")
                ).count()
            else:
                valid_count = col_data.filter(col(col_name).isNotNull()).count()
            
            validity_score = valid_count / total_count if total_count > 0 else 1.0
            validation_results[col_name] = {
                'validity_score': validity_score,
                'data_type': col_type,
                'valid_records': valid_count,
                'total_records': total_count
            }
        
        overall_validity = sum(
            result['validity_score'] for result in validation_results.values()
        ) / len(validation_results) if validation_results else 1.0
        
        return {
            'overall_validity': overall_validity,
            'column_validations': validation_results
        }
    
    def generate_quality_report(self, df: DataFrame) -> Dict[str, Any]:
        """Generate comprehensive data quality report"""
        logger.info("Starting data quality validation...")
        
        completeness = self.validate_completeness(df)
        uniqueness = self.validate_uniqueness(df)
        validity = self.validate_data_types(df)
        
        # Calculate overall quality score
        overall_score = (
            completeness['completeness_score'] * 0.3 +
            uniqueness['uniqueness_score'] * 0.3 +
            validity['overall_validity'] * 0.4
        )
        
        quality_report = {
            'timestamp': datetime.now().isoformat(),
            'overall_quality_score': overall_score,
            'meets_threshold': overall_score >= self.quality_thresholds['completeness'],
            'completeness': completeness,
            'uniqueness': uniqueness,
            'validity': validity,
            'recommendations': self._generate_recommendations(
                completeness, uniqueness, validity
            )
        }
        
        logger.info(f"Data quality score: {overall_score:.3f}")
        return quality_report
    
    def _generate_recommendations(self, completeness: Dict, uniqueness: Dict, 
                                validity: Dict) -> List[str]:
        """Generate actionable recommendations based on quality metrics"""
        recommendations = []
        
        if completeness['completeness_score'] < self.quality_thresholds['completeness']:
            recommendations.append(
                f"Completeness below threshold ({completeness['completeness_score']:.2f}). "
                "Consider data source validation and null handling strategies."
            )
        
        if uniqueness['uniqueness_score'] < self.quality_thresholds['uniqueness']:
            recommendations.append(
                f"Uniqueness below threshold ({uniqueness['uniqueness_score']:.2f}). "
                f"Found {uniqueness['duplicate_records']} duplicate records. "
                "Implement deduplication logic."
            )
        
        if validity['overall_validity'] < self.quality_thresholds['validity']:
            recommendations.append(
                f"Data validity below threshold ({validity['overall_validity']:.2f}). "
                "Review data type validations and source data quality."
            )
        
        return recommendations

class BronzeToSilverTransformer:
    """Main ETL transformation class"""
    
    def __init__(self, spark_session: SparkSession):
        self.spark = spark_session
        self.quality_validator = DataQualityValidator(spark_session)
    
    def standardize_schema(self, df: DataFrame) -> DataFrame:
        """Apply schema standardization and column naming conventions"""
        logger.info("Applying schema standardization...")
        
        # Standardize column names (lowercase, underscores)
        standardized_df = df
        for col_name in df.columns:
            new_name = (col_name
                       .lower()
                       .replace(' ', '_')
                       .replace('-', '_')
                       .replace('.', '_'))
            if col_name != new_name:
                standardized_df = standardized_df.withColumnRenamed(col_name, new_name)
        
        # Add metadata columns
        standardized_df = (standardized_df
                          .withColumn("processed_timestamp", current_timestamp())
                          .withColumn("processing_date", current_date())
                          .withColumn("data_source", lit("bronze_layer"))
                          .withColumn("etl_version", lit("1.0"))
                          .withColumn("record_hash", 
                                    sha2(concat_ws("|", *[col(c) for c in df.columns]), 256)))
        
        return standardized_df
    
    def apply_business_rules(self, df: DataFrame) -> DataFrame:
        """Apply business logic and data transformations"""
        logger.info("Applying business rules and transformations...")
        
        # Apply null handling strategies
        transformed_df = df.na.fill({
            "status": "unknown",
            "category": "other", 
            "amount": 0.0,
            "description": "not_provided"
        })
        
        # Add derived columns
        if "amount" in df.columns:
            transformed_df = transformed_df.withColumn(
                "amount_category",
                when(col("amount") > 1000, "high")
                .when(col("amount") > 100, "medium")
                .otherwise("low")
            )
        
        # Data type corrections
        if "date" in df.columns:
            transformed_df = transformed_df.withColumn(
                "date", 
                to_date(col("date"), "yyyy-MM-dd")
            )
        
        # Remove invalid records
        transformed_df = transformed_df.filter(
            col("processed_timestamp").isNotNull()
        )
        
        return transformed_df
    
    def partition_data(self, df: DataFrame, partition_columns: List[str]) -> DataFrame:
        """Prepare data for partitioned storage"""
        if "processed_timestamp" in df.columns:
            df = (df.withColumn("year", year("processed_timestamp"))
                   .withColumn("month", month("processed_timestamp"))
                   .withColumn("day", dayofmonth("processed_timestamp")))
        
        return df
    
    def transform(self, bronze_df: DataFrame, 
                 partition_columns: List[str] = None) -> Tuple[DataFrame, Dict]:
        """Main transformation pipeline"""
        logger.info("Starting Bronze to Silver transformation...")
        
        # Step 1: Generate initial quality report
        initial_quality = self.quality_validator.generate_quality_report(bronze_df)
        
        # Step 2: Schema standardization
        standardized_df = self.standardize_schema(bronze_df)
        
        # Step 3: Apply business rules
        transformed_df = self.apply_business_rules(standardized_df)
        
        # Step 4: Prepare partitioning
        if partition_columns:
            transformed_df = self.partition_data(transformed_df, partition_columns)
        
        # Step 5: Final quality validation
        final_quality = self.quality_validator.generate_quality_report(transformed_df)
        
        # Step 6: Add quality score to each record
        quality_score = final_quality['overall_quality_score']
        silver_df = transformed_df.withColumn("data_quality_score", lit(quality_score))
        
        transformation_metadata = {
            'initial_quality': initial_quality,
            'final_quality': final_quality,
            'transformation_timestamp': datetime.now().isoformat(),
            'records_processed': bronze_df.count(),
            'records_output': silver_df.count()
        }
        
        return silver_df, transformation_metadata

def create_spark_session(app_name: str) -> SparkSession:
    """Create optimized Spark session"""
    return (SparkSession.builder
            .appName(app_name)
            .config("spark.sql.adaptive.enabled", "true")
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
            .config("spark.sql.adaptive.skewJoin.enabled", "true")
            .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
            .config("spark.sql.execution.arrow.pyspark.enabled", "true")
            .getOrCreate())

def main():
    """Main ETL execution function"""
    
    # Parse job arguments
    args = getResolvedOptions(sys.argv, [
        'JOB_NAME',
        'bronze_path',
        'silver_path',
        'partition_columns',
        'quality_threshold'
    ])
    
    # Initialize contexts
    spark = create_spark_session(args['JOB_NAME'])
    sc = spark.sparkContext
    glueContext = GlueContext(sc)
    job = Job(glueContext)
    job.init(args['JOB_NAME'], args)
    
    try:
        logger.info(f"Starting ETL job: {args['JOB_NAME']}")
        logger.info(f"Bronze path: {args['bronze_path']}")
        logger.info(f"Silver path: {args['silver_path']}")
        
        # Initialize transformer
        transformer = BronzeToSilverTransformer(spark)
        
        # Read bronze data
        logger.info("Reading bronze data...")
        bronze_df = (spark.read
                    .option("multiline", "true")
                    .option("inferSchema", "true")
                    .json(args['bronze_path']))
        
        initial_count = bronze_df.count()
        logger.info(f"Read {initial_count} records from bronze layer")
        
        if initial_count == 0:
            logger.warning("No data found in bronze layer")
            job.commit()
            return
        
        # Parse partition columns
        partition_columns = (args.get('partition_columns', '').split(',') 
                           if args.get('partition_columns') else ['year', 'month'])
        
        # Transform data
        silver_df, metadata = transformer.transform(bronze_df, partition_columns)
        
        final_count = silver_df.count()
        logger.info(f"Transformed to {final_count} records for silver layer")
        
        # Quality gate check
        quality_threshold = float(args.get('quality_threshold', '0.85'))
        if metadata['final_quality']['overall_quality_score'] < quality_threshold:
            error_msg = f"Data quality ({metadata['final_quality']['overall_quality_score']:.3f}) below threshold ({quality_threshold})"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Write to silver layer
        logger.info("Writing data to silver layer...")
        (silver_df.write
         .mode("overwrite")
         .partitionBy(*partition_columns)
         .option("compression", "snappy")
         .parquet(args['silver_path']))
        
        # Save metadata
        metadata_path = f"{args['silver_path']}_metadata/transformation_metadata.json"
        metadata_df = spark.createDataFrame([json.dumps(metadata)], StringType())
        metadata_df.write.mode("overwrite").text(metadata_path)
        
        logger.info("ETL job completed successfully")
        logger.info(f"Final quality score: {metadata['final_quality']['overall_quality_score']:.3f}")
        
        job.commit()
        
    except Exception as e:
        logger.error(f"ETL job failed: {str(e)}")
        raise e
    
    finally:
        spark.stop()

if __name__ == "__main__":
    main()

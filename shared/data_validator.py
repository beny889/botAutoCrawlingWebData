import pandas as pd
import logging
from typing import Dict, List, Tuple, Any

class DataValidator:
    """Smart data validation and management for Google Sheets automation"""

    def __init__(self, unique_key: str = "Transaksi ID", composite_key_columns: List[str] = None):
        self.unique_key = unique_key
        self.composite_key_columns = composite_key_columns
        self.use_composite_key = composite_key_columns is not None
        self.logger = logging.getLogger(__name__)

    def create_composite_key(self, df: pd.DataFrame) -> pd.Series:
        """Create composite unique key by concatenating specified columns"""
        if not self.use_composite_key:
            # Use single column as before
            if self.unique_key in df.columns:
                return df[self.unique_key].astype(str)
            else:
                self.logger.warning(f"Unique key '{self.unique_key}' not found in data, using row index")
                return pd.Series(range(len(df)), index=df.index).astype(str)

        # Handle special "ALL_EXCEPT_NO" marker
        if self.composite_key_columns == "ALL_EXCEPT_NO":
            available_columns = [col for col in df.columns if col.lower() != "no"]
            self.logger.info(f"Using ALL_EXCEPT_NO: found {len(available_columns)} columns")
        else:
            # Create composite key from specified columns
            available_columns = [col for col in self.composite_key_columns if col in df.columns]

        if not available_columns:
            self.logger.warning(f"No available columns for composite key generation")
            return pd.Series(range(len(df)), index=df.index).astype(str)

        self.logger.info(f"Creating composite keys from columns: {available_columns}")

        composite_keys = []
        for _, row in df.iterrows():
            # Concatenate all specified columns with null-safe handling
            key_parts = []
            for col in available_columns:
                value = str(row[col]) if pd.notna(row[col]) and row[col] != '' else 'NULL'
                key_parts.append(value)

            composite_key = "||".join(key_parts)  # Use || as separator to avoid conflicts
            composite_keys.append(composite_key)

        return pd.Series(composite_keys, index=df.index)

    def read_existing_sheet_data(self, sheet) -> pd.DataFrame:
        """Read existing data from Google Sheets"""
        try:
            existing_data = sheet.get_all_records()
            if not existing_data:
                self.logger.info("Sheet is empty - no existing data")
                return pd.DataFrame()
            
            df = pd.DataFrame(existing_data)
            self.logger.info(f"Read {len(df)} existing records from sheet")
            return df
        except Exception as e:
            self.logger.warning(f"Could not read existing sheet data: {str(e)}")
            return pd.DataFrame()
    
    def identify_duplicates(self, new_data: pd.DataFrame, existing_data: pd.DataFrame) -> Dict[str, List[int]]:
        """Identify duplicate records based on unique key (single or composite)"""
        if existing_data.empty:
            return {"duplicates": [], "new": list(range(len(new_data)))}

        # Create composite keys for both datasets
        try:
            existing_keys = set(self.create_composite_key(existing_data))
            new_keys = self.create_composite_key(new_data)
        except Exception as e:
            self.logger.warning(f"Error creating composite keys: {e}")
            return {"duplicates": [], "new": list(range(len(new_data)))}

        duplicates = []
        new_records = []

        for idx, key in enumerate(new_keys):
            if str(key) in existing_keys:
                duplicates.append(idx)
            else:
                new_records.append(idx)

        self.logger.info(f"Found {len(duplicates)} duplicates, {len(new_records)} new records")
        return {"duplicates": duplicates, "new": new_records}
    
    def compare_data_changes(self, new_data: pd.DataFrame, existing_data: pd.DataFrame) -> Dict[str, List[int]]:
        """Compare data to find updates in existing records"""
        if existing_data.empty:
            return {"updated": [], "unchanged": []}

        updated = []
        unchanged = []

        try:
            # Create composite keys for lookup
            existing_keys = self.create_composite_key(existing_data)
            new_keys = self.create_composite_key(new_data)

            # Create lookup for existing data using composite keys
            existing_lookup = {}
            for idx, key in enumerate(existing_keys):
                existing_lookup[str(key)] = existing_data.iloc[idx].to_dict()

            # Compare new data with existing
            for idx, key in enumerate(new_keys):
                key_str = str(key)
                if key_str in existing_lookup:
                    # Compare row content (excluding index)
                    new_row_dict = new_data.iloc[idx].to_dict()
                    existing_row_dict = existing_lookup[key_str]

                    # Check if any values are different
                    has_changes = False
                    for col in new_row_dict.keys():
                        if col in existing_row_dict:
                            if str(new_row_dict[col]) != str(existing_row_dict[col]):
                                has_changes = True
                                break

                    if has_changes:
                        updated.append(idx)
                    else:
                        unchanged.append(idx)

        except Exception as e:
            self.logger.warning(f"Error comparing data changes: {e}")
            return {"updated": [], "unchanged": []}

        self.logger.info(f"Found {len(updated)} updated records, {len(unchanged)} unchanged records")
        return {"updated": updated, "unchanged": unchanged}
    
    def categorize_data(self, new_data: pd.DataFrame, existing_data: pd.DataFrame) -> Dict[str, Any]:
        """Categorize new data: new, duplicate, updated, unchanged"""
        duplicate_analysis = self.identify_duplicates(new_data, existing_data)
        
        # For duplicate records, check if they have updates
        duplicate_indices = duplicate_analysis["duplicates"]
        if duplicate_indices:
            duplicate_subset = new_data.iloc[duplicate_indices]
            change_analysis = self.compare_data_changes(duplicate_subset, existing_data)

            # FIXED: Map back to original indices safely
            updated = []
            unchanged = []

            for i in change_analysis["updated"]:
                if i < len(duplicate_indices):
                    updated.append(duplicate_indices[i])

            for i in change_analysis["unchanged"]:
                if i < len(duplicate_indices):
                    unchanged.append(duplicate_indices[i])
        else:
            updated = []
            unchanged = []
        
        categorization = {
            "new": duplicate_analysis["new"],
            "duplicates": duplicate_indices,
            "updated": updated,
            "unchanged": unchanged,
            "summary": {
                "total_records": len(new_data),
                "new_count": len(duplicate_analysis["new"]),
                "duplicate_count": len(duplicate_indices),
                "updated_count": len(updated),
                "unchanged_count": len(unchanged)
            }
        }
        
        self.logger.info(f"Data categorization: {categorization['summary']}")
        return categorization
    
    def prepare_smart_upload_data(self, new_data: pd.DataFrame, existing_data: pd.DataFrame, 
                                 handle_duplicates: str = "skip") -> Dict[str, Any]:
        """Prepare data for smart upload based on categorization"""
        categorization = self.categorize_data(new_data, existing_data)
        
        upload_plan = {
            "append_data": pd.DataFrame(),
            "update_data": pd.DataFrame(), 
            "skip_data": pd.DataFrame(),
            "operations": []
        }
        
        # Handle new records - always append
        if categorization["new"]:
            upload_plan["append_data"] = new_data.iloc[categorization["new"]]
            upload_plan["operations"].append(f"APPEND {len(categorization['new'])} new records")
        
        # Handle updated records
        if categorization["updated"]:
            upload_plan["update_data"] = new_data.iloc[categorization["updated"]]
            upload_plan["operations"].append(f"UPDATE {len(categorization['updated'])} changed records")
        
        # Handle duplicates based on strategy
        if categorization["unchanged"]:
            if handle_duplicates == "skip":
                upload_plan["skip_data"] = new_data.iloc[categorization["unchanged"]]
                upload_plan["operations"].append(f"SKIP {len(categorization['unchanged'])} unchanged duplicates")
            elif handle_duplicates == "force_update":
                upload_plan["update_data"] = pd.concat([upload_plan["update_data"], 
                                                       new_data.iloc[categorization["unchanged"]]])
                upload_plan["operations"].append(f"FORCE UPDATE {len(categorization['unchanged'])} duplicates")
        
        return upload_plan
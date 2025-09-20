import pandas as pd
import logging
from typing import Dict, List, Tuple, Any

class DataValidator:
    """Smart data validation and management for Google Sheets automation"""
    
    def __init__(self, unique_key: str = "Transaksi ID"):
        self.unique_key = unique_key
        self.logger = logging.getLogger(__name__)
    
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
        """Identify duplicate records based on unique key"""
        if existing_data.empty or self.unique_key not in new_data.columns:
            return {"duplicates": [], "new": list(range(len(new_data)))}
        
        if self.unique_key not in existing_data.columns:
            self.logger.warning(f"Unique key '{self.unique_key}' not found in existing data")
            return {"duplicates": [], "new": list(range(len(new_data)))}
        
        existing_keys = set(existing_data[self.unique_key].astype(str))
        new_keys = new_data[self.unique_key].astype(str)
        
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
        if existing_data.empty or self.unique_key not in new_data.columns or self.unique_key not in existing_data.columns:
            return {"updated": [], "unchanged": []}
        
        updated = []
        unchanged = []
        
        # Create lookup for existing data
        existing_lookup = {}
        for idx, row in existing_data.iterrows():
            key = str(row[self.unique_key])
            existing_lookup[key] = row.to_dict()
        
        # Compare new data with existing
        for idx, row in new_data.iterrows():
            key = str(row[self.unique_key])
            if key in existing_lookup:
                # Compare row content (excluding index)
                new_row_dict = row.to_dict()
                existing_row_dict = existing_lookup[key]
                
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
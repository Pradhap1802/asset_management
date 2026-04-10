#!/usr/bin/env python3
"""
Translation Update Script for Asset Management Module

This script helps maintain and update translation files for the Asset Management module.
It can be used to:
1. Extract new translatable strings from the codebase
2. Update existing translation files with new strings
3. Validate translation file format

Usage:
    python update_translations.py [--extract] [--validate] [--update]

Options:
    --extract    Extract translatable strings from source code
    --validate   Validate existing translation files
    --update     Update translation files with new strings
"""

import os
import sys
import argparse
import re
from pathlib import Path

class TranslationManager:
    def __init__(self, module_path):
        self.module_path = Path(module_path)
        self.i18n_path = self.module_path / 'i18n'
        self.supported_languages = ['es', 'fr', 'de', 'pt', 'it']
        
    def extract_translatable_strings(self):
        """Extract translatable strings from Python and XML files"""
        translatable_strings = set()
        
        # Extract from Python files
        for py_file in self.module_path.rglob('*.py'):
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # Find _('string') patterns
                matches = re.findall(r"_\(['\"]([^'\"]+)['\"]\)", content)
                translatable_strings.update(matches)
        
        # Extract from XML files
        for xml_file in self.module_path.rglob('*.xml'):
            with open(xml_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # Find string="..." patterns
                matches = re.findall(r'string="([^"]+)"', content)
                translatable_strings.update(matches)
        
        return sorted(translatable_strings)
    
    def validate_translation_file(self, po_file):
        """Validate a .po file format"""
        try:
            with open(po_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Check for required headers
            required_headers = [
                'Project-Id-Version:',
                'Content-Type: text/plain; charset=UTF-8',
                'Content-Transfer-Encoding: 8bit'
            ]
            
            for header in required_headers:
                if header not in content:
                    print(f"❌ Missing header in {po_file.name}: {header}")
                    return False
            
            # Check for msgid/msgstr pairs
            msgid_count = content.count('msgid "')
            msgstr_count = content.count('msgstr "')
            
            if msgid_count != msgstr_count:
                print(f"❌ Mismatched msgid/msgstr pairs in {po_file.name}")
                return False
            
            print(f"✅ {po_file.name} is valid")
            return True
            
        except Exception as e:
            print(f"❌ Error validating {po_file.name}: {e}")
            return False
    
    def update_translation_file(self, po_file, new_strings):
        """Update a translation file with new strings"""
        try:
            with open(po_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find existing strings
            existing_strings = set()
            msgid_pattern = r'msgid "([^"]+)"'
            matches = re.findall(msgid_pattern, content)
            existing_strings.update(matches)
            
            # Find new strings to add
            new_strings_to_add = set(new_strings) - existing_strings
            
            if new_strings_to_add:
                # Add new strings to the file
                new_entries = []
                for string in sorted(new_strings_to_add):
                    new_entries.append(f'\n#. module: asset_management\nmsgid "{string}"\nmsgstr ""\n')
                
                # Insert before the last empty line
                lines = content.split('\n')
                insert_index = len(lines) - 1
                while insert_index > 0 and lines[insert_index].strip() == '':
                    insert_index -= 1
                
                lines[insert_index:insert_index] = new_entries
                
                with open(po_file, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))
                
                print(f"✅ Added {len(new_strings_to_add)} new strings to {po_file.name}")
            else:
                print(f"ℹ️  No new strings to add to {po_file.name}")
                
        except Exception as e:
            print(f"❌ Error updating {po_file.name}: {e}")
    
    def run_extract(self):
        """Extract translatable strings"""
        print("🔍 Extracting translatable strings...")
        strings = self.extract_translatable_strings()
        print(f"Found {len(strings)} translatable strings:")
        for string in strings[:10]:  # Show first 10
            print(f"  - {string}")
        if len(strings) > 10:
            print(f"  ... and {len(strings) - 10} more")
        return strings
    
    def run_validate(self):
        """Validate all translation files"""
        print("🔍 Validating translation files...")
        all_valid = True
        for lang in self.supported_languages:
            po_file = self.i18n_path / f'{lang}.po'
            if po_file.exists():
                if not self.validate_translation_file(po_file):
                    all_valid = False
            else:
                print(f"❌ Translation file not found: {po_file}")
                all_valid = False
        
        if all_valid:
            print("✅ All translation files are valid")
        else:
            print("❌ Some translation files have issues")
        
        return all_valid
    
    def run_update(self):
        """Update all translation files with new strings"""
        print("🔄 Updating translation files...")
        strings = self.extract_translatable_strings()
        
        for lang in self.supported_languages:
            po_file = self.i18n_path / f'{lang}.po'
            if po_file.exists():
                self.update_translation_file(po_file, strings)
            else:
                print(f"❌ Translation file not found: {po_file}")

def main():
    parser = argparse.ArgumentParser(description='Asset Management Translation Manager')
    parser.add_argument('--extract', action='store_true', help='Extract translatable strings')
    parser.add_argument('--validate', action='store_true', help='Validate translation files')
    parser.add_argument('--update', action='store_true', help='Update translation files')
    
    args = parser.parse_args()
    
    # Get module path (assuming script is in i18n directory)
    script_dir = Path(__file__).parent
    module_path = script_dir.parent
    
    manager = TranslationManager(module_path)
    
    if args.extract:
        manager.run_extract()
    elif args.validate:
        manager.run_validate()
    elif args.update:
        manager.run_update()
    else:
        # Run all operations if no specific option is provided
        print("🚀 Running all translation operations...")
        manager.run_extract()
        print()
        manager.run_validate()
        print()
        manager.run_update()

if __name__ == '__main__':
    main()

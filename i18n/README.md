# Asset Management Module - Internationalization (i18n)

This directory contains translation files for the Asset Management module, supporting multiple languages for global deployment.

## Supported Languages

The module currently supports the following languages:

- **Spanish (es)** - Español
- **French (fr)** - Français  
- **German (de)** - Deutsch
- **Portuguese (pt)** - Português
- **Italian (it)** - Italiano

## Translation Files

Each language has its own `.po` file:

- `es.po` - Spanish translations
- `fr.po` - French translations
- `de.po` - German translations
- `pt.po` - Portuguese translations
- `it.po` - Italian translations

## How to Use

### Automatic Language Detection
Odoo will automatically load the appropriate translation file based on the user's language preference set in their profile.

### Manual Language Selection
Users can change their language preference by:
1. Going to **Settings** → **Users & Companies** → **Users**
2. Editing their user profile
3. Setting the **Language** field to their preferred language
4. Saving the changes

### For Administrators
To enable translations for all users:
1. Go to **Settings** → **Translations** → **Load a Translation**
2. Select the desired language
3. Choose **Load** to install the translation

## Translation Coverage

The translation files include translations for:

- **Model Names**: All asset management models
- **Field Labels**: All form field labels and descriptions
- **Field Help Text**: Help text for all fields
- **Selection Values**: All dropdown/selection field values
- **Error Messages**: Validation and error messages
- **Security Groups**: User group names and categories
- **Menu Items**: Navigation menu labels
- **Button Labels**: Action button text
- **Status Values**: Asset status and transfer status values

## Adding New Languages

To add support for additional languages:

1. Create a new `.po` file in this directory (e.g., `nl.po` for Dutch)
2. Copy the structure from an existing translation file
3. Translate all `msgstr` values to the target language
4. Update the `__manifest__.py` file to include the new translation file
5. Test the translations in Odoo

### Translation File Structure

```po
#. module: asset_management
#: model:ir.model.fields,field_description:asset_management.field_asset_management__name
msgid "Asset Reference"
msgstr "Translated Text Here"
```

## Quality Assurance

All translations have been reviewed for:
- **Accuracy**: Correct translation of technical terms
- **Consistency**: Consistent terminology throughout the module
- **Context**: Appropriate translations for business context
- **Completeness**: All translatable strings are covered

## Contributing

If you find translation errors or want to improve existing translations:

1. Edit the appropriate `.po` file
2. Update the `msgstr` value with the corrected translation
3. Test the changes in Odoo
4. Submit your improvements

## Technical Notes

- Translation files use the GNU gettext `.po` format
- All files use UTF-8 encoding
- Translation keys are automatically generated from the source code
- Odoo handles the loading and caching of translations automatically

## Support

For translation-related issues or questions:
- Check the Odoo documentation on internationalization
- Review the translation files for consistency
- Test translations in a development environment before production use

---

**Note**: This module follows Odoo's standard internationalization practices and is compatible with Odoo's built-in translation management system.

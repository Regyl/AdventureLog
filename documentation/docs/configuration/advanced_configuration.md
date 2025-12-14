# Advanced Configuration

In addition to the primary configuration variables listed above, there are several optional environment variables that can be set to further customize your AdventureLog instance. These variables are not required for a basic setup but can enhance functionality and security.

| Name                         | Required | Description                                                                                                                                                                                | Default Value |
| ---------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------- |
| `ACCOUNT_EMAIL_VERIFICATION` | No       | Enable email verification for new accounts. Options are `none`, `optional`, or `mandatory`                                                                                                 | `none`        |
| `FORCE_SOCIALACCOUNT_LOGIN`  | No       | When set to `True`, only social login is allowed (no password login). The login page will show only social providers or redirect directly to the first provider if only one is configured. | `False`       |

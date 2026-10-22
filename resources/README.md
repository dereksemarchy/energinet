# resources/ — what is deployed next to the data product, not by its build

The data product build (`sem-design`) compiles `src/`. Everything here is deployed **separately**,
with the `sem` Platform CLI, and the data product only *names* it. Fill these folders per project.

| Folder | Content | Deployed with | Required? |
|---|---|---|---|
| `RestClient/` | One JSON per REST client used by a `RestClientEnricher` (file name = client name) | `sem dm admin rest-clients set <name> -i …` | When the data product calls one |
| `image-libraries/` | Icons, avatars, logos and covers (flat-fill SVGs, zipped with Python) | `sem dm admin image-libraries import <lib> -i …` | When the data product references `images://<lib>/…` |
| `data/` | Demo / seed datasets + their loader | REST loads API (dry-run first) | No |
| `platform-administration/roles/` | **One JSON per role the data product references** | `sem dm admin roles set <role> -i …` | **Yes** — a role granted privileges in the data product but absent from the platform makes those privileges inoperative |
| `platform-administration/role-mapping/` | IdP groups → roles | `sem dm admin role-mapping get` → merge → `set` (tenant-wide: it **replaces** the whole mapping) | No — SSO projects |
| `platform-administration/api-keys/` | Integration key definitions (never the key value) | `sem dm admin api-keys create -i …` | No — loads through the REST API |
| `platform-administration/notification-servers/` | SMTP server definitions (secrets as placeholders) | `sem dm admin notification-servers set <name> -i …` | No — needed for workflow emails and notification policies |
| `platform-administration/variable-providers/` | Value providers for dynamic variables other than SemQL | `sem dm admin variable-providers set <name> -i …` | When a dynamic variable uses one |
| `data-location/notification-policies/` | Alerts on job outcomes | `sem dm data-locations notification-policies set <name> --data-location-name <DL> -i …` | No |
| `data-location/data-notifications/` | Push changed records (named query) to a REST / Kafka / JMS target | `sem dm data-locations data-notifications set <name> --data-location-name <DL> -i …` | No |
| `data-location/continuous-loads/` | Loads submitted on a fixed interval | `sem dm data-locations continuous-loads set <name> --data-location-name <DL> -i …` | No |
| `data-location/purge-schedule/` | When the retention policies are applied | `sem dm data-locations purge-schedule set --data-location-name <DL> -i …` | No — but retention policies that purge never run without it |
| `DEPLOYMENT.md` | The project's deployment runbook | — | Recommended |

**Generate the payloads from the data product** instead of writing them by hand — the script reads
`src/<Model>`, says what the data product calls for and why, writes the role payloads (mandatory) and
the scaffolds you ask for, and flags every `<placeholder>` left to fill:

```bash
python ai-model-development/scripts/platform_resources.py src/<Model>                          # report
python ai-model-development/scripts/platform_resources.py src/<Model> --write                  # roles
python ai-model-development/scripts/platform_resources.py src/<Model> --write --include all    # + every optional scaffold
```

Never commit a secret: SMTP passwords, target API keys and the like stay `<placeholders>` here and
are filled in at deploy time. Details: `ai-model-development/cli/PlatformCLI/PLATFORM-CLI.md`
§ *Platform resources for a complete deployment*.

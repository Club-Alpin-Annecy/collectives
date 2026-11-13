# Pull request previews

`.github/workflows/preview.yml` builds the image of each pull request, pushes
it to `ghcr.io/club-alpin-annecy/collectives:pr-<number>`, then runs
`collectives-preview deploy <number>` on the preview server through SSH. The
instance is served on `https://pr-<number>.test.collectives.cafannecy.fr` with
its own MariaDB database `pr_<number>`; both are removed when the pull request
is closed. Pull requests from forks wait for a maintainer approval. After
each deployment, a comment on the pull request gives the url and the
password of the `admin` account, generated for each instance.

## Server setup

Ubuntu with [once](https://github.com/basecamp/once)
(`curl https://get.once.com | sh`), and a DNS record
`*.test.collectives.cafannecy.fr` pointing to the server.

```sh
# MariaDB root password, and the secrets of each instance (root only)
echo "MARIADB_ROOT_PASSWORD=$(openssl rand -hex 24)" \
    | sudo install -m 600 /dev/stdin /etc/collectives-preview.env
sudo install -d -m 700 /var/lib/collectives-preview

# MariaDB, reachable only from the once network
sudo sh -c '. /etc/collectives-preview.env; docker run -d --name collectives-mariadb \
    --restart unless-stopped --network once -v collectives-mariadb:/var/lib/mysql \
    -e MARIADB_ROOT_PASSWORD="$MARIADB_ROOT_PASSWORD" --memory 768m mariadb:10.11 \
    --innodb-buffer-pool-size=256M \
    --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci'

# deploy user, whose SSH key can only run collectives-preview
sudo install -m 755 collectives-preview /usr/local/bin/
sudo useradd -m -s /bin/sh deploy
echo 'deploy ALL=(root) NOPASSWD: /usr/local/bin/collectives-preview' \
    | sudo install -m 440 /dev/stdin /etc/sudoers.d/collectives-preview
ssh-keygen -t ed25519 -N '' -C github-preview -f preview_key
echo "restrict,command=\"/usr/local/bin/collectives-preview\" $(cat preview_key.pub)" \
    | sudo install -D -m 644 /dev/stdin ~deploy/.ssh/authorized_keys  # owned by root
```

On GitHub, create the environments `preview` and `preview-fork` (the latter
with required reviewers), store `preview_key` as the secret `PREVIEW_SSH_KEY`
of both, then delete it. After the first push, make the `collectives` package
public so that the server can pull it.

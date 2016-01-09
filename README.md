# docker-compose-mixer

Package which allow to run docker-compose with several docker-compose.yml files

## Installation (only for UNIX & MacOS)

* Download bin file `sudo wget https://github.com/paunin/docker-compose-mixer/blob/master/dist/dc-mixer?raw=true -O /usr/local/bin/dc-mixer`
* Make it executable `sudo chmod +x /usr/local/bin/dc-mixer`
* Run it as console command `dc-mixer` from directory with `docker-compose-mixer.yml` file

## Internal flow

* get containers definitions
* change services names
* resolving services names as atomic operation with:
    * remove ignored services (all from `ignores` section of config)
    * remove links to ignored services
* resolve paths
* resolving ports conflicts (to avoid binding the same ports from different files)
* apply `overrides`
* add master services


## Configuration and syntax

By default Mixer uses file in the same directory with name `docker-compose-mixer.yml`


### Includes

```yaml
includes:
  proja: projectA/docker-compose.yml
  projb: projectB/docker-compose.yml
...
```

Based on this configuration  all services from `projectA` in result file will change names and will have prefix `proja`
That means prefixes should contain only allowed symbols according docker-compose syntax.

If `projectA/docker-compose.yml` contains code:

```yaml
mysql:
  image: mysql:latest

pgsql:
  image: postgres:latest

php:
  build: images/php
  links:
    - pgsql
    - mysql:database
  volumes_from:
    - pgsql
```

...and `projectB/docker-compose.yml` contains code:

```yaml
pgsql:
  build: images/pgsql
```


In result file you will see configuration:

```yaml
projamysql:
  image: mysql:latest

projapgsql:
  image: postgres:latest

projaphp:
  build: projectA/images/php
  links:
    - projapgsql:pgsql
    - projamysql:database
  volumes_from:
    - projapgsql

projbpgsql:
  build: projectB/images/pgsql
```

That means Mixer added prefix to services names and solved problems in names conflicts with using aliases.
Resolving names conflicts is available for:

* `links`
* `volumes_from`
* `container_name` (if only container name defined it will be changed with prefix after processing)
* `extends.service` (if only `extends.file` not defined)

Also in example above you can see that Mixer changed paths to build:
Resolving paths is available for:

* `build`
* `volumes`
* `env_file`
* `extends`

### Overrides

```yaml
...
overrides:
  projaphp:
    ports:
      - 80:80
    links:
      - projbpgsql:pgsql

  projbphp:
    ports:
      - 81:80
...
```

In section `overrides` you can define values to merge in result file.

#### NOTES:
* Ports you defined in overrides will be in result file without changes. Mixer will not try to solve conflicts in overrides.
* To redefine values for paths (e.g. `build`, `voluems`) be sure paths will be related to `docker-compose-mixer.yml` file
* If you want redefine attribute which should contain array, keep in mind:
 **your array will be in result file without any merging to original value** (e.g. ports, links)

### Master services

If you want to link services from two(or more) different `docker-compose.yml`, you have to define it in `overrides`
or create another service where you will define links. In section `master_services` you must define normal

```yaml
...
master_services:
  php:
    ports:
      8080:80
    links:
      - projbpgsql:pgsql
      - projamysql:mysql
    volumes_from:
      - projaphp
```

#### NOTES:
* Any services in `master_services` section will be in result file *without any changes*.
* You have to use names of services with prefixes because of... @see case above ;)

### Ignores

```yaml
...
ignores:
  - projbpgsql
```

This section will remove services from result file and will check if any service linked with it and clean it as well.
Cleaning available for same services where resolving names conflicts available.

If services uses for `extend` directive, child service will be ignored as well

## Result

File `docker-compose.yml` will be result of Mixer job.
You can put that file in `.gitignore` if you will use Mixer every build.

After run of Mixer you can work with `docker-compose.yml` file like you do with any docker-compose configurations.

## Examples

More examples you can find in [examples](./examples) directory.

## Copyright

* [Dmitriy Paunin](http://paunin.com) <d.m.paunin@gmail.com>

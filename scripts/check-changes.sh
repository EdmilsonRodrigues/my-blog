#!/usr/bin/sh

get_suffix() {
    _start="$1"
    _sep="${2-/}"
    awk -v start="$_start" -v sep="$_sep" '
        BEGIN { FS=sep }
        {
            for (i = start; i < NF; i++)
                printf $i FS
            file_parts_n = split($i, file_parts, /\./)
            for (j = 1; j < file_parts_n; j++)
                no_suffix = no_suffix file_parts[j] "."
            print no_suffix
        }'
}

get_missing_files() {
    _to=$1
    _from=$2
    _missing=""

    for file in $_from
    do
        if ! echo " $_to " | grep -qF " $file "
        then
            _missing="$_missing $file"
        fi
    done

    echo "$_missing"
}

check_templates() {
    _files_changed=$1
    _files_output=$2

    if ! echo " $_files_changed " | grep -Fq '/templates/'
    then
        return 0
    fi

    changed_languages=$(echo "$_files_changed" | awk '
        BEGIN { RS=" "; FS ="/" }
        $2 == "templates" {
            changed_templates[$1] = 1
        }
        END {
            for (language in changed_templates) {
                print language
            }
        }
    ')

    IFS="\n"; for lan in $changed_languages
              do

              done

    find -type file --exclude="templates"

    echo "$_files_output"

    return 0
}

main() {
    _modified_files=$(git status --porcelain=v2 | awk '$2 ~ /[^.]./ && $9 ~ /^static\// { print $9 }')

    _contents=""
    _dist=""
    _contents_relative=""
    _dist_relative=""
    for file in $_modified_files
    do
        src=$(echo "$file" | cut -d '/' -f 2)
        if [ "$src" = "content" ]
        then
            _contents="$_contents $file"
            _contents_relative=$(echo "$file" | get_suffix 3 "/")
        elif [ "$src" = "dist" ]
        then
            _dist="$_dist $file"
            _dist_relative=$(echo "$file" | get_suffix 3 "/")
        fi
    done

    _missing_files=$(get_missing_files "$_dist_relative" "$_contents_relative")

    if [ -n "$_missing_files" ]
    then
        echo "The following files were changed in contents, but not in dist: $_missing_files" >> /dev/stderr
        echo "Run C-c C-e P x to publish them." >> /dev/stderr
        exit 1
    fi

    check_templates "$_contents_relative" "$_dist_relative"
    exit $?
}

main


function ctf-setup {
    if [[ $# -ne 1 ]]; then
        echo "Usage: $0 <target>"
        return 1
    fi

    export t=${1}

    # Prefer tun0; fall back to the primary (ethernet) interface
    l=$(ip -4 -o addr show dev tun0 2>/dev/null | awk '{print $4}' | cut -d/ -f1)

    if [[ -z $l ]]; then
        local eth
        eth=$(ip route | awk '/default/ {for(i=1;i<=NF;i++) if($i=="dev") print $(i+1); exit}')
        l=$(ip -4 -o addr show dev "$eth" 2>/dev/null | awk '{print $4}' | cut -d/ -f1)
    fi

    export l
    echo "Set up environment: l=${l} t=${t}"
}

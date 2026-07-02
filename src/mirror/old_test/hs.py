import click

@click.group()
def cli():
    pass

@cli.command()
@click.argument("host")
@click.option("--port", default=8000, help="监听端口")
def start(host, port):
    """启动服务"""
    click.echo(f"Starting server at {host}:{port}")

@cli.command()
@click.argument("pid", type=int)
def stop(pid):
    """停止服务"""
    click.echo(f"Stopping process {pid}")



port_file = resources.files("mirror.mirror_control").joinpath("settings/Domestic_Amplifier_Mapping.csv") if self.is_domestic else resources.files("mirror.mirror_control").joinpath("settings/Imported_Amplifier_Mapping.csv")
amplifers = _load_hardware_config(port_file, col=1, defaults=DEFAULT_AMP_PORTS)

if __name__ == "__main__":
    cli()

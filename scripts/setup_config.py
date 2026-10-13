#!/usr/bin/env python3
"""
GPU Finder - Utilitário de Configuração Inicial e Atualização de Credenciais.
Usado pelo instalador automático ou executado diretamente pelo usuário.
"""

import argparse
import getpass
import os
import sys
from pathlib import Path

# Adiciona a raiz do projeto ao PYTHONPATH
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import load_config, save_config, CONFIG_PATH

def configure_app(
    email: str = None,
    password: str = None,
    center_city: str = None,
    radius_km: float = None,
    interactive: bool = True
):
    example_path = PROJECT_ROOT / "config.example.yaml"
    if not CONFIG_PATH.exists() and example_path.exists():
        CONFIG_PATH.write_text(example_path.read_text(encoding="utf-8"), encoding="utf-8")

    config = load_config()

    if interactive and (email is None and password is None):
        print("\n" + "=" * 60)
        print("🔑 CONFIGURAÇÃO DE CREDENCIAIS DO FACEBOOK MARKETPLACE")
        print("=" * 60)
        print("O Facebook Marketplace requer credenciais para desbloquear")
        print("a busca regionalizada contínua na Serra Gaúcha.")
        print("(Pressione ENTER sem digitar nada para manter o valor atual ou pular)\n")

        curr_email = config.scrapers.facebook.email or ""
        email_prompt = f"E-mail do Facebook [{curr_email}]: " if curr_email else "E-mail do Facebook: "
        user_email = input(email_prompt).strip()
        if user_email:
            email = user_email
        elif curr_email:
            email = curr_email

        if email:
            has_pass = bool(config.scrapers.facebook.password)
            pass_prompt = "Senha do Facebook (oculta) [manter atual]: " if has_pass else "Senha do Facebook (oculta): "
            user_pass = getpass.getpass(pass_prompt).strip()
            if user_pass:
                password = user_pass
            elif has_pass:
                password = config.scrapers.facebook.password

        print("\n" + "=" * 60)
        print("📍 LOCALIZAÇÃO E RAIO DE PESQUISA")
        print("=" * 60)
        curr_city = config.location.center_city or "Veranópolis"
        user_city = input(f"Cidade Centro de Referência [{curr_city}]: ").strip()
        if user_city:
            center_city = user_city

        curr_radius = config.location.radius_km or 50
        user_radius = input(f"Raio de Busca em KM [{curr_radius}]: ").strip()
        if user_radius:
            try:
                radius_km = float(user_radius)
            except ValueError:
                print(f"⚠️ Raio inválido, mantendo {curr_radius}km")

    # Aplica alterações
    if email is not None:
        config.scrapers.facebook.email = email
    if password is not None:
        config.scrapers.facebook.password = password
    if center_city:
        config.location.center_city = center_city
    if radius_km is not None and radius_km > 0:
        config.location.radius_km = radius_km

    save_config(config)

    # Restringe permissões do config.yaml para leitura/escrita apenas pelo proprietário
    try:
        os.chmod(CONFIG_PATH, 0o600)
    except Exception as e:
        print(f"Aviso de permissão: {e}")

    print("\n✅ Configurações salvas com sucesso em config.yaml (permissões 600)!")
    if config.scrapers.facebook.email:
        print(f"   👤 Facebook: {config.scrapers.facebook.email} (senha configurada)")
    else:
        print("   ℹ️ Facebook: Acesso anônimo/cookies locais.")
    print(f"   📍 Cidade Centro: {config.location.center_city} (Raio {config.location.radius_km}km)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Configurador do GPU Finder")
    parser.add_argument("--email", type=str, help="E-mail do Facebook")
    parser.add_argument("--password", type=str, help="Senha do Facebook")
    parser.add_argument("--center-city", type=str, help="Cidade centro de referência")
    parser.add_argument("--radius", type=float, help="Raio em km")
    parser.add_argument("--non-interactive", action="store_true", help="Não solicitar dados pelo terminal")

    args = parser.parse_args()
    configure_app(
        email=args.email,
        password=args.password,
        center_city=args.center_city,
        radius_km=args.radius,
        interactive=not args.non_interactive
    )

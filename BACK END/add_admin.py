"""
Script para agregar usuarios admin a la base de datos
Uso: python add_admin.py <email> <username> <password> <full_name>
"""

import sys
import os
from pathlib import Path

# Agregar el directorio actual al path
sys.path.insert(0, str(Path(__file__).parent))

from main import User, SessionLocal
from passlib.context import CryptContext

# Configurar contexto de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def add_admin_user(email: str, username: str, password: str, full_name: str = "Admin"):
    """Agregar un usuario admin a la base de datos"""
    
    db = SessionLocal()
    
    try:
        # Verificar si el usuario ya existe
        existing_user = db.query(User).filter(
            (User.email == email) | (User.username == username)
        ).first()
        
        if existing_user:
            print(f"❌ Error: El usuario con email '{email}' o username '{username}' ya existe")
            return False
        
        # Hash de la contraseña
        hashed_password = pwd_context.hash(password)
        
        # Crear nuevo usuario admin
        new_user = User(
            email=email,
            username=username,
            hashed_password=hashed_password,
            full_name=full_name,
            role="admin",
            is_active=True
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        print(f"✅ Usuario admin creado exitosamente:")
        print(f"   Email: {email}")
        print(f"   Username: {username}")
        print(f"   Nombre: {full_name}")
        print(f"   Rol: admin")
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error al crear el usuario: {str(e)}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Uso: python add_admin.py <email> <username> <password> [full_name]")
        print("\nEjemplos:")
        print("  python add_admin.py admin@admin.com admingc4td4sxo securepass123 'Admin Admin'")
        print("  python add_admin.py nuevo@admin.com newadmin password123")
        sys.exit(1)
    
    email = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]
    full_name = sys.argv[4] if len(sys.argv) > 4 else "Admin"
    
    add_admin_user(email, username, password, full_name)

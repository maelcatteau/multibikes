# Module MultiBikes Website

## Description

Ce module étend les fonctionnalités du site web e-commerce MultiBikes en ajoutant plusieurs fonctionnalités essentielles pour la gestion des locations de vélos:

1. **Visibilité des tarifs** - Ajout d'un champ booléen `mb_website_published` au modèle `product.pricing` permettant de contrôler précisément quels tarifs sont visibles sur le site web.

2. **Durées minimales de location saisonnières** - Configuration de trois périodes distinctes (basse, moyenne et haute saison) avec des durées minimales de location spécifiques pour chaque période.

3. **Filtrage dynamique des tarifs** - Modification de l'affichage des tarifs dans la table de prix sur le site web en fonction du paramètre de visibilité.

4. **Calcul dynamique des contraintes de location** - Ajustement automatique des durées minimales de location en fonction de la date sélectionnée par le client.

## Fonctionnalités techniques

### Gestion des tarifs
- Ajout du champ `mb_website_published` au modèle `product.pricing`
- Surcharge de la méthode `_get_additionnal_combination_info` pour filtrer les tarifs affichés
- Optimisation pour n'afficher que le meilleur tarif par période (le moins cher)

### Gestion des périodes saisonnières
- Configuration de trois périodes distinctes dans les paramètres de la société:
  - Période 1 (généralement basse saison): dates de début/fin et durée minimale
  - Période 2 (généralement moyenne saison): dates de début/fin et durée minimale
  - Période 3 (généralement haute saison): dates de début/fin et durée minimale
- Interface de configuration accessible via les paramètres du site web

### API et contrôleurs
- Surcharge du contrôleur `/rental/product/constraints` pour renvoyer des durées minimales dynamiques
- Gestion des formats de date multiples pour une meilleure compatibilité

### Interface utilisateur
- Mise à jour dynamique des durées minimales affichées sur le site web
- Adaptation de l'interface JavaScript pour refléter les contraintes saisonnières
- Amélioration de l'expérience utilisateur lors de la sélection des dates de location

## Dépendances

- `website_sale_renting` - Module de base pour la location sur le site web
- `multibikes_base` - Module de base MultiBikes avec les fonctionnalités communes

## Installation

1. Placez ce module dans le répertoire `custom-addons` de votre installation Odoo
2. Mettez à jour la liste des modules dans Odoo
3. Installez le module via l'interface d'administration d'Odoo
4. Redémarrez le serveur pour appliquer les modifications

## Configuration

### Configuration des périodes saisonnières
1. Accédez à **Site Web > Configuration > Paramètres**
2. Dans l'onglet **MultiBikes**, définissez:
   - Les dates de début et fin pour chaque période saisonnière
   - La durée minimale de location pour chaque période
   - L'unité de temps pour chaque durée minimale (heures, jours, semaines)

### Configuration de la visibilité des tarifs
1. Accédez à **MultiBikes > Configuration > Tarification**
2. Pour chaque tarif, cochez ou décochez la case **Visible sur le site web**
3. Seuls les tarifs marqués comme visibles apparaîtront dans la table de tarification du site web

## Utilisation technique

### Calcul dynamique des durées minimales

```python
def get_dynamic_renting_minimal_duration(self, reference_date=None):
    """
    Calcule la durée minimale de location en fonction de la date de référence.
    Si aucune date n'est fournie, utilise la date actuelle.
    Retourne un tuple (durée, unité)
    """
    # Vérification des périodes et retour de la durée minimale appropriée
    if self.mb_renting_period1_start_date <= reference_date <= self.mb_renting_period1_end_date:
        return (self.mb_renting_period1_minimal_time_duration, self.mb_renting_period1_minimal_time_unit)
    # Vérification des autres périodes...
```

### Filtrage des tarifs visibles

```python
# Filtrer les tarifs publiés
all_suitable_pricings = ProductPricing._get_suitable_pricings(product_or_template, pricelist)
published_pricings = all_suitable_pricings.filtered(lambda p: p.mb_website_published)
```

## Support et maintenance

Pour toute question ou problème concernant ce module, veuillez contacter l'équipe de développement MultiBikes.

## Licence

Ce module est distribué sous licence LGPL-3.

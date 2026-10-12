package com.example.culinaria

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.fragment.app.Fragment
import com.example.culinaria.databinding.ActivityMainBinding
import com.example.culinaria.fragment.CategoriasFragment
import com.example.culinaria.fragment.CardapioSemanalFragment
import com.example.culinaria.fragment.EditarFragment
import com.example.culinaria.fragment.NovaReceitaFragment
import com.example.culinaria.fragment.ReceitasFragment

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        if (savedInstanceState == null) {
            loadFragment(ReceitasFragment())
        }

        binding.bottomNavigation.setOnItemSelectedListener { menuItem ->
            when (menuItem.itemId) {
                R.id.nav_home -> loadFragment(ReceitasFragment())
                R.id.nav_cardapio -> loadFragment(CardapioSemanalFragment())
                R.id.nav_nova -> loadFragment(NovaReceitaFragment())
                R.id.nav_editar -> loadFragment(EditarFragment())
                R.id.nav_categorias -> loadFragment(CategoriasFragment())
                else -> false
            }
            true
        }
    }

    private fun loadFragment(fragment: Fragment): Boolean {
        supportFragmentManager.beginTransaction()
            .replace(R.id.fragment_container, fragment)
            .commit()
        return true
    }
}

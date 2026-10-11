using System.Data.SqlClient;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace AtuneraPacifico.Controllers
{
    [Authorize]
    public class ProductController : Controller
    {
        public IActionResult Buscar(string nombre, SqlConnection conexion)
        {
            var consulta = "SELECT * FROM Productos WHERE Nombre = '" + nombre + "'";
            var comando = new SqlCommand(consulta, conexion);
            return Ok(comando.ExecuteScalar());
        }

        public IActionResult BuscarSeguro(string nombre, SqlConnection conexion)
        {
            using var comando = new SqlCommand("SELECT * FROM Productos WHERE Nombre = @nombre", conexion);
            comando.Parameters.AddWithValue("@nombre", nombre);
            return Ok(comando.ExecuteScalar());
        }

        public IActionResult Descargar(string archivo)
        {
            var contenido = System.IO.File.ReadAllText("/var/reportes/" + archivo);
            return Content(contenido);
        }

        public async Task<IActionResult> Vista(string url, HttpClient cliente)
        {
            var html = await cliente.GetStringAsync(url);
            return Content(html);
        }

        public IActionResult Exportar(string formato)
        {
            System.Diagnostics.Process.Start("cmd.exe", "/c exportar.bat " + formato);
            return Ok();
        }

        [HttpPost]
        public IActionResult Eliminar(int id)
        {
            return Ok(id);
        }
    }
}

// RoslynBridge
//
// Recibe la ruta de una carpeta de solución .NET, parsea cada archivo .cs
// con la interfaz de programación Roslyn (Microsoft.CodeAnalysis.CSharp) y
// escribe a stdout el AST simplificado que consume el motor de reglas en
// Python (ver backend/engine/ast_bridge.py para el esquema exacto).
//
// Uso:
//   dotnet run --project roslyn-bridge -- <ruta-a-la-solucion>

using System.Text.Json;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;

if (args.Length == 0)
{
    Console.Error.WriteLine("Uso: RoslynBridge <ruta-a-la-solucion>");
    return 1;
}

var raiz = args[0];
var archivosCs = Directory.EnumerateFiles(raiz, "*.cs", SearchOption.AllDirectories);

var resultados = new List<object>();

foreach (var ruta in archivosCs)
{
    var texto = File.ReadAllText(ruta);
    var arbol = CSharpSyntaxTree.ParseText(texto);
    var raizSintaxis = arbol.GetCompilationUnitRoot();
    var rutaRelativa = Path.GetRelativePath(raiz, ruta).Replace('\\', '/');

    resultados.Add(new
    {
        file = rutaRelativa,
        loc = texto.Split('\n').Length,
        declarations = ExtraerDeclaraciones(raizSintaxis, arbol),
        literals = ExtraerLiterales(raizSintaxis, arbol),
        invocations = ExtraerInvocaciones(raizSintaxis, arbol),
        disposables = ExtraerDisposables(raizSintaxis, arbol),
    });
}

Console.WriteLine(JsonSerializer.Serialize(resultados, new JsonSerializerOptions { WriteIndented = false }));
return 0;

// --- Extracción de nodos relevantes para las reglas de los cuatro módulos ---
// Nota: esta es una primera pasada de la implementación; cada extractor debe
// ampliarse conforme se agreguen las reglas restantes descritas en el
// catálogo de cincuenta reglas (sección 3.4).

static List<object> ExtraerDeclaraciones(CompilationUnitSyntax raiz, SyntaxTree arbol)
{
    var lista = new List<object>();

    foreach (var prop in raiz.DescendantNodes().OfType<PropertyDeclarationSyntax>())
    {
        lista.Add(new
        {
            kind = "property",
            name = prop.Identifier.Text,
            type = prop.Type.ToString(),
            modifiers = prop.Modifiers.Select(m => m.Text).ToArray(),
            line = arbol.GetLineSpan(prop.Span).StartLinePosition.Line + 1,
        });
    }

    foreach (var field in raiz.DescendantNodes().OfType<FieldDeclarationSyntax>())
    {
        foreach (var variable in field.Declaration.Variables)
        {
            lista.Add(new
            {
                kind = "field",
                name = variable.Identifier.Text,
                type = field.Declaration.Type.ToString(),
                modifiers = field.Modifiers.Select(m => m.Text).ToArray(),
                line = arbol.GetLineSpan(field.Span).StartLinePosition.Line + 1,
            });
        }
    }

    // TODO(módulo Rendimiento): marcar `used = false` cruzando cada variable
    // local contra su alcance (DataFlowAnalysis de Roslyn) para PERF-001.

    return lista;
}

static List<object> ExtraerLiterales(CompilationUnitSyntax raiz, SyntaxTree arbol)
{
    var lista = new List<object>();

    foreach (var asignacion in raiz.DescendantNodes().OfType<EqualsValueClauseSyntax>())
    {
        if (asignacion.Value is LiteralExpressionSyntax literal &&
            literal.IsKind(SyntaxKind.StringLiteralExpression) &&
            asignacion.Parent is VariableDeclaratorSyntax declarator)
        {
            lista.Add(new
            {
                kind = "string",
                value = literal.Token.ValueText,
                line = arbol.GetLineSpan(literal.Span).StartLinePosition.Line + 1,
                assigned_to = declarator.Identifier.Text,
            });
        }
    }

    return lista;
}

static List<object> ExtraerInvocaciones(CompilationUnitSyntax raiz, SyntaxTree arbol)
{
    var lista = new List<object>();

    foreach (var creacion in raiz.DescendantNodes().OfType<ObjectCreationExpressionSyntax>())
    {
        var tipo = creacion.Type.ToString();
        if (tipo != "SqlCommand") continue;

        var concatenado = creacion.ArgumentList?.Arguments
            .Any(a => ArgumentoEsConcatenado(a)) ?? false;

        lista.Add(new
        {
            method = "SqlCommand.ctor",
            line = arbol.GetLineSpan(creacion.Span).StartLinePosition.Line + 1,
            arguments_are_concatenated = concatenado,
        });
    }

    return lista;
}

// Determina si el argumento es una concatenación de cadenas. Cubre dos casos:
//   1. La concatenación ocurre directamente en el argumento: new SqlCommand("..." + x)
//   2. La concatenación ocurre en una variable declarada antes, dentro del mismo
//      método, y esa variable se pasa por nombre: var q = "..." + x; new SqlCommand(q)
// Nota: esto es coincidencia de patrones sintácticos de un solo nivel, no un
// análisis de flujo de datos completo (no sigue reasignaciones ni llamadas a
// otros métodos).
static bool ArgumentoEsConcatenado(ArgumentSyntax arg)
{
    if (arg.Expression is BinaryExpressionSyntax bin && bin.IsKind(SyntaxKind.AddExpression))
        return true;

    if (arg.Expression is IdentifierNameSyntax id)
    {
        var metodo = arg.FirstAncestorOrSelf<MethodDeclarationSyntax>();
        var declarador = metodo?.DescendantNodes()
            .OfType<VariableDeclaratorSyntax>()
            .FirstOrDefault(v => v.Identifier.Text == id.Identifier.Text && v.Initializer != null);

        if (declarador?.Initializer?.Value is BinaryExpressionSyntax bin2 && bin2.IsKind(SyntaxKind.AddExpression))
            return true;
    }

    return false;
}

static List<object> ExtraerDisposables(CompilationUnitSyntax raiz, SyntaxTree arbol)
{
    var lista = new List<object>();
    var tiposDisposable = new[] { "SqlConnection", "StreamWriter", "StreamReader", "FileStream" };

    foreach (var declaracion in raiz.DescendantNodes().OfType<LocalDeclarationStatementSyntax>())
    {
        if (declaracion.UsingKeyword.IsKind(SyntaxKind.UsingKeyword)) continue; // ya usa 'using var'

        foreach (var variable in declaracion.Declaration.Variables)
        {
            var tipo = ResolverTipoDeclarado(declaracion.Declaration, variable);
            if (!tiposDisposable.Contains(tipo)) continue;

            var envueltoEnUsing = declaracion.Parent is UsingStatementSyntax;

            lista.Add(new
            {
                type = tipo,
                variable = variable.Identifier.Text,
                line = arbol.GetLineSpan(declaracion.Span).StartLinePosition.Line + 1,
                wrapped_in_using = envueltoEnUsing,
                disposed_explicitly = false, // TODO: rastrear llamadas a .Dispose() en el mismo bloque
            });
        }
    }

    return lista;
}

// Si el tipo se declaró con 'var', esto no nos dice de qué tipo es en realidad.
// Sin un modelo semántico completo (que requeriría compilar con todas las
// referencias del proyecto), resolvemos el caso común: 'var x = new Tipo(...)'
// mirando el tipo del lado derecho de la asignación.
static string ResolverTipoDeclarado(VariableDeclarationSyntax declaracion, VariableDeclaratorSyntax variable)
{
    var tipoTexto = declaracion.Type.ToString();
    if (tipoTexto == "var" && variable.Initializer?.Value is ObjectCreationExpressionSyntax creacion)
        return creacion.Type.ToString();

    return tipoTexto;
}

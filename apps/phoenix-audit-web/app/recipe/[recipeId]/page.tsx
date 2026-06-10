import { notFound } from 'next/navigation'
import { RecipeView } from '@/components/artifacts/recipe-view'
import { PageShell } from '@/components/ui/page-shell'
import { RECIPE } from '@/lib/fixtures'

interface PageProps {
  params: Promise<{ recipeId: string }>
}

export default async function RecipePage({ params }: PageProps) {
  const { recipeId } = await params
  // Only the sample recipe renders here — real recipes are delivered as
  // signed Markdown URLs. Any other id must 404, never serve demo data
  // under a real-looking address.
  if (recipeId !== RECIPE.recipeId) notFound()
  return (
    <PageShell label="recipe">
      <RecipeView />
    </PageShell>
  )
}

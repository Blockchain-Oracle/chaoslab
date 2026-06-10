import { RecipeView } from '@/components/artifacts/recipe-view'
import { PageShell } from '@/components/ui/page-shell'

interface PageProps {
  params: Promise<{ recipeId: string }>
}

export default async function RecipePage({ params }: PageProps) {
  await params // route param accepted but the demo always renders the hero recipe
  return (
    <PageShell label="recipe">
      <RecipeView />
    </PageShell>
  )
}

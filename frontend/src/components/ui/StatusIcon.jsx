import {
  Activity,
  AlertTriangle,
  Award,
  BarChart3,
  BookOpen,
  Brain,
  Camera,
  Check,
  ChevronRight,
  FlaskConical,
  HelpCircle,
  Lightbulb,
  Scale,
  Shapes,
  Shield,
  Star,
  Target,
  Trophy,
  X,
  Zap,
} from 'lucide-react';

const SIZES = { xs: 12, sm: 14, md: 18, lg: 24, xl: 32 };

function iconProps(size, className) {
  return {
    size: SIZES[size] || SIZES.md,
    className,
    'aria-hidden': true,
    strokeWidth: 2,
  };
}

/** Verified / broken / warning for audit steps and outcomes */
export function StatusIcon({ status, size = 'md', className = '' }) {
  const p = iconProps(size, className);
  switch (status) {
    case 'good':
      return <Check {...p} />;
    case 'bad':
      return <X {...p} />;
    case 'warn':
      return <AlertTriangle {...p} />;
    default:
      return <HelpCircle {...p} />;
  }
}

export function OnboardingIcon({ name, className = 'text-accent' }) {
  const p = iconProps('xl', className);
  switch (name) {
    case 'target':
      return <Target {...p} />;
    case 'scale':
      return <Scale {...p} />;
    case 'flask':
      return <FlaskConical {...p} />;
    case 'shapes':
      return <Shapes {...p} />;
    case 'trophy':
      return <Trophy {...p} />;
    default:
      return <Target {...p} />;
  }
}

export function AchievementIcon({ name, className = 'text-warn-foreground' }) {
  const p = iconProps('md', className);
  switch (name) {
    case 'target':
      return <Target {...p} />;
    case 'activity':
      return <Activity {...p} />;
    case 'zap':
      return <Zap {...p} />;
    case 'shield':
      return <Shield {...p} />;
    case 'chart':
      return <BarChart3 {...p} />;
    case 'award':
      return <Award {...p} />;
    case 'brain':
      return <Brain {...p} />;
    case 'star':
      return <Star {...p} />;
    case 'trophy':
      return <Trophy {...p} />;
    case 'book':
      return <BookOpen {...p} />;
    default:
      return <HelpCircle {...p} />;
  }
}

export {
  AlertTriangle,
  Camera,
  Check,
  ChevronRight,
  FlaskConical,
  HelpCircle,
  Lightbulb,
  Scale,
  Shapes,
  Target,
  X,
};
